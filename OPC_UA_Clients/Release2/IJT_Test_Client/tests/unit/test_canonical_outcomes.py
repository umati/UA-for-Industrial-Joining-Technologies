"""
Unit tests for helpers/canonical_outcomes.py

The canonical model is the single vocabulary source for final reports.
These tests pin the deterministic mappings from every detailed vocabulary
(readiness/execution, raw pytest/JUnit, CU compliance rollup) so a mapping
change cannot silently alter what a report says.
No OPC UA server required.
"""

from __future__ import annotations

import pytest

from helpers.canonical_outcomes import (
    ALL_OUTCOMES,
    CANONICAL_OUTCOME_LABELS,
    CANONICAL_OUTCOME_ORDER,
    CATEGORY_CLAIM,
    CATEGORY_CONNECTIVITY,
    CATEGORY_OPERATOR_ACTION,
    CATEGORY_SAFETY_POLICY,
    CATEGORY_UNKNOWN,
    OUTCOME_BLOCKED,
    OUTCOME_CLAIM_MISMATCH,
    OUTCOME_CONFIGURATION_ERROR,
    OUTCOME_FAILED,
    OUTCOME_MANUAL_REQUIRED,
    OUTCOME_PASSED,
    OUTCOME_UNSUPPORTED,
    REASON_CLAIM_METHOD_MISSING,
    REASON_ENDPOINT_UNREACHABLE,
    REASON_MANUAL_TRIGGER_REQUIRED,
    REASON_UNSAFE_METHOD_NOT_ENABLED,
    CanonicalFinding,
    CanonicalOutcome,
    canonical_for_legacy_outcome,
    canonical_for_pytest_outcome,
    canonical_for_report_outcome,
    canonical_label,
    canonical_outcome,
    finding_from_legacy,
    reason_category,
    worst_canonical_outcome,
)

# ---------------------------------------------------------------------------
# The canonical vocabulary itself
# ---------------------------------------------------------------------------


class TestCanonicalVocabulary:
    def test_exactly_six_canonical_outcomes(self):
        assert len(CanonicalOutcome) == 6

    def test_every_outcome_has_a_public_label(self):
        assert set(CANONICAL_OUTCOME_LABELS) == set(CanonicalOutcome)
        assert len(set(CANONICAL_OUTCOME_LABELS.values())) == 6

    def test_public_labels_are_stable(self):
        assert CanonicalOutcome.PASSED.label == "Passed"
        assert CanonicalOutcome.FAILED.label == "Failed"
        assert CanonicalOutcome.NOT_SUPPORTED.label == "Not Supported"
        assert CanonicalOutcome.BLOCKED.label == "Blocked"
        assert CanonicalOutcome.NOT_TESTED.label == "Not Tested"
        assert CanonicalOutcome.INCONCLUSIVE.label == "Inconclusive"

    def test_report_order_covers_every_outcome_worst_first(self):
        assert set(CANONICAL_OUTCOME_ORDER) == set(CanonicalOutcome)
        assert CANONICAL_OUTCOME_ORDER[0] is CanonicalOutcome.FAILED
        assert CANONICAL_OUTCOME_ORDER[-1] is CanonicalOutcome.PASSED

    def test_actionable_and_informational_partitions(self):
        assert CanonicalOutcome.FAILED.is_actionable
        assert CanonicalOutcome.BLOCKED.is_actionable
        assert CanonicalOutcome.INCONCLUSIVE.is_actionable
        assert CanonicalOutcome.NOT_SUPPORTED.is_informational
        assert CanonicalOutcome.NOT_TESTED.is_informational
        assert not CanonicalOutcome.PASSED.is_actionable
        assert not CanonicalOutcome.PASSED.is_informational

    def test_coercion_accepts_value_and_enum(self):
        assert canonical_outcome("passed") is CanonicalOutcome.PASSED
        assert canonical_outcome(CanonicalOutcome.BLOCKED) is CanonicalOutcome.BLOCKED
        assert canonical_outcome("  NOT_TESTED ") is CanonicalOutcome.NOT_TESTED

    def test_coercion_rejects_unknown_value(self):
        with pytest.raises(ValueError):
            canonical_outcome("almost_passed")

    def test_label_helper_falls_back_to_inconclusive(self):
        assert canonical_label("failed") == "Failed"
        assert canonical_label("nonsense") == "Inconclusive"

    def test_worst_outcome_picks_the_most_severe(self):
        assert worst_canonical_outcome(["passed", "not_supported", "blocked"]) is CanonicalOutcome.BLOCKED
        assert worst_canonical_outcome(["passed", "failed"]) is CanonicalOutcome.FAILED
        assert worst_canonical_outcome([]) is CanonicalOutcome.NOT_TESTED
        assert worst_canonical_outcome(None) is CanonicalOutcome.NOT_TESTED


# ---------------------------------------------------------------------------
# Legacy readiness/execution outcomes
# ---------------------------------------------------------------------------


class TestLegacyOutcomeMapping:
    @pytest.mark.parametrize(
        ("legacy", "expected"),
        [
            (OUTCOME_PASSED, CanonicalOutcome.PASSED),
            (OUTCOME_FAILED, CanonicalOutcome.FAILED),
            (OUTCOME_BLOCKED, CanonicalOutcome.BLOCKED),
            (OUTCOME_MANUAL_REQUIRED, CanonicalOutcome.BLOCKED),
            (OUTCOME_CLAIM_MISMATCH, CanonicalOutcome.FAILED),
            (OUTCOME_CONFIGURATION_ERROR, CanonicalOutcome.INCONCLUSIVE),
        ],
    )
    def test_claim_independent_outcomes(self, legacy, expected):
        assert canonical_for_legacy_outcome(legacy) is expected
        assert canonical_for_legacy_outcome(legacy, claimed=True) is expected

    def test_unclaimed_unsupported_is_informational(self):
        assert canonical_for_legacy_outcome(OUTCOME_UNSUPPORTED) is CanonicalOutcome.NOT_SUPPORTED

    def test_claimed_unsupported_is_a_failure(self):
        assert canonical_for_legacy_outcome(OUTCOME_UNSUPPORTED, claimed=True) is CanonicalOutcome.FAILED

    def test_every_legacy_outcome_is_mapped(self):
        for legacy in ALL_OUTCOMES:
            assert isinstance(canonical_for_legacy_outcome(legacy), CanonicalOutcome)

    def test_unknown_legacy_outcome_is_inconclusive(self):
        assert canonical_for_legacy_outcome("who_knows") is CanonicalOutcome.INCONCLUSIVE


# ---------------------------------------------------------------------------
# Raw pytest / JUnit outcomes
# ---------------------------------------------------------------------------


class TestPytestOutcomeMapping:
    @pytest.mark.parametrize(
        ("outcome", "expected"),
        [
            ("passed", CanonicalOutcome.PASSED),
            ("failed", CanonicalOutcome.FAILED),
            ("error", CanonicalOutcome.FAILED),
            ("blocked", CanonicalOutcome.BLOCKED),
            ("environment", CanonicalOutcome.BLOCKED),
            ("accepted_policy", CanonicalOutcome.NOT_SUPPORTED),
            ("skipped", CanonicalOutcome.NOT_TESTED),
            ("untested", CanonicalOutcome.NOT_TESTED),
            ("xfailed", CanonicalOutcome.INCONCLUSIVE),
            ("xpassed", CanonicalOutcome.INCONCLUSIVE),
        ],
    )
    def test_raw_outcomes(self, outcome, expected):
        assert canonical_for_pytest_outcome(outcome) is expected

    def test_not_supported_depends_on_the_claim(self):
        assert canonical_for_pytest_outcome("not_supported") is CanonicalOutcome.NOT_SUPPORTED
        assert canonical_for_pytest_outcome("not_supported", claimed=True) is CanonicalOutcome.FAILED

    def test_case_and_whitespace_insensitive(self):
        assert canonical_for_pytest_outcome(" PASSED ") is CanonicalOutcome.PASSED

    def test_unknown_outcome_is_inconclusive(self):
        assert canonical_for_pytest_outcome("weird") is CanonicalOutcome.INCONCLUSIVE


# ---------------------------------------------------------------------------
# CU compliance rollups
# ---------------------------------------------------------------------------


class TestReportOutcomeMapping:
    @pytest.mark.parametrize(
        ("outcome", "expected"),
        [
            ("supported", CanonicalOutcome.PASSED),
            ("partial", CanonicalOutcome.INCONCLUSIVE),
            ("blocked", CanonicalOutcome.BLOCKED),
            ("action_needed", CanonicalOutcome.FAILED),
            ("untested", CanonicalOutcome.NOT_TESTED),
            ("unknown", CanonicalOutcome.INCONCLUSIVE),
        ],
    )
    def test_rollups(self, outcome, expected):
        assert canonical_for_report_outcome(outcome) is expected

    def test_claimed_but_not_supported_is_a_failure(self):
        assert canonical_for_report_outcome("not_supported") is CanonicalOutcome.NOT_SUPPORTED
        assert canonical_for_report_outcome("not_supported", claimed=True) is CanonicalOutcome.FAILED


# ---------------------------------------------------------------------------
# Reason codes and categories stay separate from the outcome
# ---------------------------------------------------------------------------


class TestReasonCategories:
    def test_known_reason_codes_have_categories(self):
        assert reason_category(REASON_ENDPOINT_UNREACHABLE) == CATEGORY_CONNECTIVITY
        assert reason_category(REASON_CLAIM_METHOD_MISSING) == CATEGORY_CLAIM
        assert reason_category(REASON_UNSAFE_METHOD_NOT_ENABLED) == CATEGORY_SAFETY_POLICY
        assert reason_category(REASON_MANUAL_TRIGGER_REQUIRED) == CATEGORY_OPERATOR_ACTION

    def test_unknown_reason_code_is_unknown_category(self):
        assert reason_category("brand_new_reason") == CATEGORY_UNKNOWN
        assert reason_category("") == CATEGORY_UNKNOWN


class TestCanonicalFinding:
    def test_finding_preserves_detail_next_to_the_outcome(self):
        finding = finding_from_legacy(
            OUTCOME_BLOCKED,
            reason_code=REASON_MANUAL_TRIGGER_REQUIRED,
            detail="Operator must trigger the tool",
            evidence={"tool": "TOOL-1"},
        )
        assert isinstance(finding, CanonicalFinding)
        assert finding.outcome is CanonicalOutcome.BLOCKED
        assert finding.label == "Blocked"
        assert finding.source_outcome == OUTCOME_BLOCKED
        assert finding.reason_code == REASON_MANUAL_TRIGGER_REQUIRED
        assert finding.reason_category == CATEGORY_OPERATOR_ACTION

    def test_finding_serialises_for_final_reports(self):
        payload = finding_from_legacy(
            OUTCOME_UNSUPPORTED,
            reason_code=REASON_CLAIM_METHOD_MISSING,
            detail="Method absent",
            claimed=True,
        ).to_dict()
        assert payload["canonical_outcome"] == "failed"
        assert payload["canonical_label"] == "Failed"
        assert payload["source_outcome"] == "unsupported"
        assert payload["reason_category"] == CATEGORY_CLAIM
        assert "evidence" not in payload

    def test_finding_includes_evidence_when_present(self):
        payload = finding_from_legacy(OUTCOME_FAILED, evidence={"node": "ns=2;i=5"}).to_dict()
        assert payload["evidence"] == {"node": "ns=2;i=5"}
