"""Unit tests for report_scoring helpers."""

from helpers.report_scoring import (
    conformance_score,
    delta_symbol,
    format_pct,
    pct_value,
)


def test_pct_value_returns_none_for_zero_denominator():
    """Test that pct_value returns None when denominator is zero."""
    assert pct_value(10, 0) is None
    assert pct_value(0, 0) is None
    assert pct_value(5, -1) is None


def test_format_pct_handles_non_numeric_values():
    """Test that format_pct returns 'n/a' for non-numeric values."""
    assert format_pct(None) == "n/a"
    assert format_pct("not a number") == "n/a"
    assert format_pct([1, 2, 3]) == "n/a"
    assert format_pct(42) == "42.0%"
    assert format_pct(98.5) == "98.5%"


def test_conformance_score_returns_zero_for_invalid_inputs():
    """Test that conformance_score returns 0 for invalid inputs."""
    counts = {"supported": 10, "partial": 5, "action_needed": 0, "blocked": 0}

    # Non-integer server_supported_count
    assert conformance_score(counts, "invalid", 100) == 0
    assert conformance_score(counts, None, 100) == 0

    # Zero or negative server_supported_count
    assert conformance_score(counts, 0, 100) == 0
    assert conformance_score(counts, -1, 100) == 0

    # Zero or negative total_active_profile_cus
    assert conformance_score(counts, 50, 0) == 0
    assert conformance_score(counts, 50, -1) == 0


def test_delta_symbol_returns_empty_for_missing_baseline():
    """Test that delta_symbol returns empty string when baseline is missing."""
    assert delta_symbol("cu_001", "passed", None) == ""
    assert delta_symbol("cu_001", "passed", {}) == ""
    assert delta_symbol("cu_001", "passed", {"cu_outcomes": {}}) == ""


def test_delta_symbol_returns_empty_for_untested_in_either():
    """Test that delta_symbol returns empty when either current or previous is untested."""
    baseline = {"cu_outcomes": {"cu_001": "untested"}}
    assert delta_symbol("cu_001", "passed", baseline) == ""
    assert delta_symbol("cu_001", "untested", baseline) == ""


def test_delta_symbol_returns_new_for_new_cu():
    """Test that delta_symbol returns 'New' for CUs not in baseline."""
    baseline = {"cu_outcomes": {"cu_001": "passed"}}
    assert delta_symbol("cu_002", "passed", baseline) == "New"


def test_delta_symbol_returns_checkmark_for_unchanged():
    """Test that delta_symbol returns checkmark for unchanged outcome."""
    baseline = {"cu_outcomes": {"cu_001": "passed"}}
    assert delta_symbol("cu_001", "passed", baseline) == "✓"


def test_delta_symbol_returns_arrows_for_rank_changes():
    """Test that delta_symbol returns arrows for outcome rank changes."""
    baseline = {"cu_outcomes": {"cu_001": "blocked"}}

    # Improvement (higher rank)
    assert delta_symbol("cu_001", "not_supported", baseline) == "↑"

    # Regression (lower rank)
    baseline = {"cu_outcomes": {"cu_002": "not_supported"}}
    assert delta_symbol("cu_002", "blocked", baseline) == "↓"


def test_delta_symbol_returns_empty_for_unknown_outcomes():
    """Test that delta_symbol returns empty for unknown outcome ranks."""
    baseline = {"cu_outcomes": {"cu_001": "unknown_outcome"}}
    assert delta_symbol("cu_001", "passed", baseline) == ""

    baseline = {"cu_outcomes": {"cu_001": "passed"}}
    assert delta_symbol("cu_001", "unknown_outcome", baseline) == ""
