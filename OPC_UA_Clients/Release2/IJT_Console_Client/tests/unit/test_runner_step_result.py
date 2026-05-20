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

_RUNNER_DIR = Path(__file__).parents[2]  # = IJT_Console_Client/
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


def test_semgrep_https_preflight_checks_rules_endpoint(monkeypatch):
    seen: list[str] = []

    class _Response:
        def raise_for_status(self) -> None:
            return None

    class _Requests:
        @staticmethod
        def get(url: str, timeout: float):
            seen.append(url)
            assert timeout == 5.0
            return _Response()

    monkeypatch.setitem(sys.modules, "requests", _Requests)

    assert _mod._is_https_reachable("semgrep.dev")
    assert seen == ["https://semgrep.dev/c/p/default"]


def test_pypi_https_preflight_checks_json_endpoint(monkeypatch):
    seen: list[str] = []

    class _Response:
        def raise_for_status(self) -> None:
            return None

    class _Requests:
        @staticmethod
        def get(url: str, timeout: float):
            seen.append(url)
            assert timeout == 5.0
            return _Response()

    monkeypatch.setitem(sys.modules, "requests", _Requests)

    assert _mod._is_https_reachable("pypi.org")
    assert seen == ["https://pypi.org/pypi/pip/json"]


def test_pip_audit_timeout_is_advisory_skip():
    timeout_output = "[TIMEOUT] Command exceeded 30s limit: pip-audit\n"
    with (
        patch.object(_mod, "_tool_available", return_value=True),
        patch.object(_mod, "_is_https_reachable", return_value=True),
        patch.object(Path, "mkdir", return_value=None),
        patch.object(Path, "write_text", return_value=None),
        patch.object(_mod, "_run", return_value=(1, timeout_output)) as run_cmd,
    ):
        result = _mod._step_pip_audit()

    assert result.ok
    assert result.skipped
    assert "network unavailable" in result.note
    command = run_cmd.call_args.args[0]
    assert "--progress-spinner" in command
    assert "--timeout" in command
    assert "--cache-dir" in command
    assert run_cmd.call_args.kwargs["timeout_label"] == "pip-audit"


def test_run_uses_own_process_group_on_posix(monkeypatch, tmp_path):
    captured_kwargs: dict[str, Any] = {}

    class _FakeProcess:
        pid = 12345
        returncode = 0

        def __init__(self, *_args, **kwargs):
            captured_kwargs.update(kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def communicate(self, timeout):
            assert timeout == 10
            return "ok\n", ""

    monkeypatch.setattr(_mod.sys, "platform", "linux")
    monkeypatch.setattr(_mod.subprocess, "Popen", _FakeProcess)

    rc, output = _mod._run(["python", "--version"], cwd=tmp_path, timeout=10)

    assert rc == 0
    assert output == "ok\n"
    assert captured_kwargs["start_new_session"] is True


def test_security_matrix_step_uses_configured_wall_clock_timeout(monkeypatch, tmp_path):
    calls: list[dict[str, Any]] = []

    def _fake_run(_cmd, **kwargs):
        calls.append(kwargs)
        return 0, "33 passed in 1.23s"

    monkeypatch.setattr(_mod, "_RESULTS_DIR", tmp_path)
    monkeypatch.setattr(_mod, "_tool_available", lambda _name: False)
    monkeypatch.setattr(_mod, "_run", _fake_run)

    result = _mod._step_security_matrix_tests("B1", "windows", 40461)

    assert result.ok
    assert calls
    assert calls[0]["timeout"] == _mod._SECURITY_MATRIX_TIMEOUT_SEC
    assert calls[0]["timeout_label"] == "Console security matrix B1"


def test_install_requirements_preserves_explicit_pip_cache_dir(monkeypatch, tmp_path):
    venv = tmp_path / ".venv_test"
    venv.mkdir()
    requirements = tmp_path / "requirements.txt"
    requirements_dev = tmp_path / "requirements-dev.txt"
    requirements.write_text("PyYAML>=6.0\n", encoding="utf-8")
    requirements_dev.write_text("urllib3>=2.7.0\n", encoding="utf-8")
    caller_cache = tmp_path / "caller-pip-cache"
    runner_cache = tmp_path / "tmp" / "pip-cache"
    envs: list[dict[str, str]] = []

    def fake_check_call(_cmd, **kwargs):
        envs.append(kwargs["env"])

    monkeypatch.setattr(_mod, "_VENV", venv)
    monkeypatch.setattr(_mod, "_REQUIREMENTS", requirements)
    monkeypatch.setattr(_mod, "_REQUIREMENTS_DEV", requirements_dev)
    monkeypatch.setattr(_mod, "_TMP_DIR", tmp_path / "tmp")
    monkeypatch.setattr(_mod, "_venv_pip", lambda path: Path("pip"))
    monkeypatch.setattr(_mod, "_venv_python", lambda path: Path("python"))
    monkeypatch.setattr(_mod.subprocess, "check_call", fake_check_call)
    monkeypatch.setenv("PIP_CACHE_DIR", str(caller_cache))
    monkeypatch.delenv("SKIP_VENV_INSTALL", raising=False)

    _mod._install_requirements()

    assert envs
    assert all(env["PIP_CACHE_DIR"] == str(caller_cache) for env in envs)
    assert not runner_cache.exists()


# ---------------------------------------------------------------------------
# Suite counter logic — mirrors the counters in main()
# ---------------------------------------------------------------------------


def _counts(results: list) -> dict:
    """Replicate the exact counter logic from Console Client main()."""
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


def _run_semgrep_step_with_findings(findings: list):
    payload = {"results": findings, "errors": []}

    with (
        patch.object(_mod, "_binary_available", return_value=True),
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
