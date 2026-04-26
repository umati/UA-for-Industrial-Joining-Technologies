"""
Unit tests for _StepResult (run_all_tests.py runner infrastructure).

Guards the PASS / WARN / FAIL / SKIP state model so advisory tools
like Semgrep can never accidentally block the suite.

Key invariants tested:
  - warn=True  → shows as WARN, excluded from both passed and failed counts
  - ok=False   → shows as FAIL, counted in failed (blocks suite)
  - ok=True    → shows as PASS, counted in passed
  - skipped=True → shows as SKIP, excluded from all outcome counts
  - Semgrep parse-failure path produces warn=True (non-blocking by design)
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Import _StepResult from run_all_tests.py (the runner script, not a package)
# ---------------------------------------------------------------------------

_RUNNER_DIR = Path(__file__).parents[2]  # = IJT_Test_Client/
sys.path.insert(0, str(_RUNNER_DIR))
_mod = importlib.import_module("run_all_tests")
# Assign as Any so mypy can resolve attribute access on dynamically-imported class
_StepResult: Any = _mod._StepResult


# ---------------------------------------------------------------------------
# _StepResult state model
# ---------------------------------------------------------------------------


def test_default_state_is_fail():
    """Freshly created _StepResult defaults to FAIL (ok=False, warn=False, skipped=False)."""
    r = _StepResult("label")
    assert not r.ok
    assert not r.warn
    assert not r.skipped


def test_pass_state():
    r = _StepResult("label")
    r.ok = True
    assert r.ok
    assert not r.warn
    assert not r.skipped


def test_warn_state_is_not_ok_and_not_fail():
    """warn=True must be distinct from both ok=True (PASS) and ok=False (FAIL)."""
    r = _StepResult("label")
    r.warn = True
    assert r.warn
    assert not r.skipped


def test_skip_state():
    r = _StepResult("label")
    r.skipped = True
    r.ok = True
    assert r.skipped


# ---------------------------------------------------------------------------
# Suite counter logic — mirrors the counters in main()
# ---------------------------------------------------------------------------


def _counts(results: list) -> dict:
    """Replicate the exact counter logic from Test Client main()."""
    passed = sum(1 for r in results if r.ok and not r.skipped and not r.warn)
    warned = sum(1 for r in results if r.warn and not r.skipped)
    failed = sum(1 for r in results if not r.ok and not r.skipped and not r.warn)
    skipped = sum(1 for r in results if r.skipped)
    return {"passed": passed, "warned": warned, "failed": failed, "skipped": skipped}


def _make(*, ok: bool = False, warn: bool = False, skipped: bool = False):
    r = _StepResult("x")
    r.ok = ok
    r.warn = warn
    r.skipped = skipped
    return r


def test_counter_warn_does_not_count_as_failed():
    """A WARN result must not increment the failed counter."""
    results = [_make(warn=True)]
    c = _counts(results)
    assert c["failed"] == 0
    assert c["warned"] == 1
    assert c["passed"] == 0


def test_counter_warn_does_not_count_as_passed():
    """A WARN result must not inflate the passed counter."""
    results = [_make(ok=True, warn=True)]
    c = _counts(results)
    assert c["passed"] == 0
    assert c["warned"] == 1


def test_counter_fail_increments_failed():
    results = [_make(ok=False)]
    c = _counts(results)
    assert c["failed"] == 1
    assert c["warned"] == 0


def test_counter_mixed_suite_warn_does_not_cause_suite_fail():
    """Suite with one WARN and all others PASS must still report failed=0."""
    results = [
        _make(ok=True),
        _make(ok=True),
        _make(warn=True),  # advisory — must not block suite
        _make(ok=True),
    ]
    c = _counts(results)
    assert c["failed"] == 0
    assert c["warned"] == 1
    assert c["passed"] == 3
    any_failed = c["failed"] > 0
    assert not any_failed


# ---------------------------------------------------------------------------
# Semgrep parse-failure path: non-blocking by contract
# ---------------------------------------------------------------------------


def _run_semgrep_step_with_bad_json():
    """Run _step_semgrep() with a corrupt semgrep.json so the except branch fires."""
    with (
        patch.object(_mod, "_binary_available", return_value=True),
        patch.object(_mod, "_ensure_cli_tool", return_value=(True, "")),
        patch.object(_mod, "_RESULTS_DIR", _RUNNER_DIR),
        patch.object(_mod, "_run", return_value=(0, "")),
        patch.object(Path, "exists", return_value=True),
        patch("pathlib.Path.read_text", return_value="NOT VALID JSON ]["),
    ):
        result = _mod._step_semgrep()
    return result


def test_semgrep_parse_failure_sets_warn_not_fail():
    """Semgrep parse failure must set warn=True (advisory), never ok=False (FAIL)."""
    result = _run_semgrep_step_with_bad_json()
    assert result.warn, "Semgrep parse failure must set warn=True"
    assert not result.skipped, "Semgrep parse failure must not mark as skipped"


def test_semgrep_parse_failure_does_not_block_suite():
    """Semgrep parse failure result must not count as suite failure."""
    result = _run_semgrep_step_with_bad_json()
    c = _counts([result])
    assert c["failed"] == 0, "Semgrep advisory failure must not appear in failed count"


def test_semgrep_parse_failure_note_contains_advisory():
    """Semgrep parse failure note must contain clear diagnostic info (parse failed + rc)."""
    result = _run_semgrep_step_with_bad_json()
    note_lower = result.note.lower()
    assert "parse failed" in note_lower or "rc=" in note_lower, (
        f"Semgrep parse-failure note must contain diagnostic info (parse failed / rc=); got: {result.note!r}"
    )


# ---------------------------------------------------------------------------
# Semgrep no-output-file path: network/auth failure — non-blocking by contract
# ---------------------------------------------------------------------------


def _run_semgrep_step_with_no_output_file():
    """Run _step_semgrep() simulating the real-world case where semgrep exits
    without writing semgrep.json (e.g. network unavailable for p/default rules)."""
    with (
        patch.object(_mod, "_binary_available", return_value=True),
        patch.object(_mod, "_ensure_cli_tool", return_value=(True, "")),
        patch.object(_mod, "_RESULTS_DIR", _RUNNER_DIR),
        patch.object(_mod, "_run", return_value=(-1, "")),
        patch.object(Path, "exists", return_value=False),
    ):
        result = _mod._step_semgrep()
    return result


def test_semgrep_no_output_file_sets_warn_not_fail():
    """When semgrep produces no output file it must be advisory WARN, never FAIL."""
    result = _run_semgrep_step_with_no_output_file()
    assert result.warn, "No-output-file path must set warn=True"
    assert not result.skipped, "No-output-file path must not mark as skipped"


def test_semgrep_no_output_file_does_not_block_suite():
    """No-output-file path must not appear as a suite failure."""
    result = _run_semgrep_step_with_no_output_file()
    c = _counts([result])
    assert c["failed"] == 0, "No-output-file must not appear in failed count"


def test_semgrep_no_output_file_note_mentions_network():
    """No-output-file note must mention network or authentication so the cause is clear."""
    result = _run_semgrep_step_with_no_output_file()
    note_lower = result.note.lower()
    assert "network" in note_lower or "auth" in note_lower, (
        f"No-output-file note must mention network/auth; got: {result.note!r}"
    )


# ---------------------------------------------------------------------------
# Semgrep findings paths
# ---------------------------------------------------------------------------


def _run_semgrep_step_with_findings(findings: list):
    payload = {"results": findings, "errors": []}

    with (
        patch.object(_mod, "_binary_available", return_value=True),
        patch.object(_mod, "_ensure_cli_tool", return_value=(True, "")),
        patch.object(_mod, "_is_https_reachable", return_value=True),
        patch.object(_mod, "_RESULTS_DIR", _RUNNER_DIR),
        patch.object(_mod, "_run", return_value=(0, "")),
        patch.object(Path, "exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=json.dumps(payload)),
    ):
        result = _mod._step_semgrep()
    return result


def test_semgrep_no_findings_is_pass():
    result = _run_semgrep_step_with_findings(findings=[])
    assert result.ok
    assert not result.warn
    assert not result.skipped


def test_semgrep_warnings_only_is_warn_not_fail():
    """Advisory warnings from Semgrep must produce WARN, not FAIL."""
    warn_finding = {"extra": {"severity": "WARNING"}, "check_id": "w1", "path": "x.py", "start": {"line": 1}}
    result = _run_semgrep_step_with_findings(findings=[warn_finding])
    assert result.warn, "Semgrep warnings must set warn=True"
    assert result.ok, "Semgrep warnings: ok should remain True (non-blocking)"
    c = _counts([result])
    assert c["failed"] == 0


def test_semgrep_errors_is_fail():
    """Semgrep ERROR findings are real code defects — must produce FAIL."""
    error_finding = {"extra": {"severity": "ERROR"}, "check_id": "e1", "path": "x.py", "start": {"line": 1}}
    result = _run_semgrep_step_with_findings(findings=[error_finding])
    assert not result.ok, "Semgrep ERROR findings must set ok=False (blocking)"
    assert not result.warn
    c = _counts([result])
    assert c["failed"] == 1
