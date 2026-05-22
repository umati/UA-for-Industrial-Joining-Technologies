"""Function-level byte-identity gate for the conformance summary renderer.

Phase 1 of the IJT CI / System Tests reporting overhaul moved
``_render(...)`` out of ``scripts/make_conformance_summary.py`` (formerly
``scripts/make_ci_summary.py``; renamed in the same commit to reflect that
this is a Test-Client conformance renderer, not a repo-wide CI summary) into
``scripts/reporting/conformance_summary.py`` as
``render_conformance_summary(...)``. These tests prove that move was
behavior-preserving: the new function reproduces the exact Markdown that
was captured from the pre-extraction renderer for two real fixtures —
the CI Test Client unit run and a representative System Tests live
conformance run.

Each test:

1. Loads ``pytest.xml`` (and, when present, ``cu_results.json`` and
   ``baseline.json``) from a captured fixture directory.
2. Calls ``render_conformance_summary(...)`` with frozen ``run_ts``,
   ``server_url``, and ``report_environment`` so wall-clock time, host
   environment, runner Python patch version, asyncua release, git SHA, or
   GitHub Actions run cannot drift the output.
3. Asserts byte-equality against the corresponding expected Markdown
   under ``fixtures/expected/``.

A separate regression test drives the renderer with deliberately altered
live-environment values and proves the byte-identity output is unchanged
when a frozen ``ReportEnvironment`` is passed. That test guards the
``Python 3.14+`` support promise: any 3.14.x patch / runner OS / asyncua
release / commit SHA / GitHub run URL must produce identical bytes.

To intentionally regenerate the expected files (review the diff before
landing), run ``python tests/unit/reporting/_capture_expected_summaries.py``
from the IJT_Test_Client directory.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

# scripts/ is not a Python package; add it to sys.path so we can import the
# renderer the same way the workflow CLI does (`python scripts/make_conformance_summary.py`
# puts scripts/ on sys.path[0]). This mirrors the existing IJT Test Client
# convention of bare module imports such as ``from helpers.cu_registry import CU``
# (see ``tests/unit/test_skip_reasons.py``).
_SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# Sibling helper modules (``_frozen_env``) live next to this test file, which
# is in a non-package directory. Make sibling imports work regardless of how
# pytest is invoked.
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from _frozen_env import FIXED_RUN_TS, FIXED_SERVER_URL, FROZEN_ENV  # noqa: E402
from make_conformance_summary import _load_baseline, _load_json, _parse  # noqa: E402
from reporting import conformance_summary as _ci_summary  # noqa: E402
from reporting.conformance_summary import (  # noqa: E402
    ReportEnvironment,
    render_conformance_summary,
)

_FIXTURES_DIR = Path(__file__).parent / "fixtures"
_EXPECTED_DIR = _FIXTURES_DIR / "expected"


@pytest.mark.parametrize(
    ("fixture_dir", "expected_file"),
    [
        ("ci_unit_no_cu_payload", "ci_unit_no_cu_payload.md"),
        ("system_tests_full_conformance", "system_tests_full_conformance.md"),
    ],
    ids=["ci_unit_no_cu_payload", "system_tests_full_conformance"],
)
def test_conformance_summary_byte_identical(fixture_dir: str, expected_file: str) -> None:
    fixt = _FIXTURES_DIR / fixture_dir
    data = _parse(fixt / "pytest.xml")

    cu_path = fixt / "cu_results.json"
    baseline_path = fixt / "baseline.json"
    cu_payload = _load_json(cu_path) if cu_path.exists() else None
    baseline = _load_baseline(baseline_path) if baseline_path.exists() else None

    produced, _context = render_conformance_summary(
        data,
        FIXED_SERVER_URL,
        FIXED_RUN_TS,
        cu_payload,
        baseline,
        report_environment=FROZEN_ENV,
    )

    expected = (_EXPECTED_DIR / expected_file).read_text(encoding="utf-8")
    assert produced == expected, (
        f"Renderer output drifted from {expected_file}. "
        "If this change is intentional, regenerate expected files with "
        "`python tests/unit/reporting/_capture_expected_summaries.py` "
        "and review the diff."
    )


def test_renderer_ignores_live_environment_when_frozen_env_passed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guard: renderer must not read live env when a frozen environment is passed.

    Drives ``render_conformance_summary`` with the same fixture inputs as the
    byte-identity test, but first replaces every live-environment read in the
    renderer module with deliberately absurd values that do not match the
    captured fixture. If the renderer leaks any of those reads into the output
    (instead of using the frozen ``ReportEnvironment``), the byte-identity
    assertion below fails — locally, before CI ever runs.

    This codifies the project's ``Python 3.14+`` support promise: any 3.14.x
    patch version, host OS, asyncua release, git SHA, or GitHub Actions run
    must produce identical bytes when the same frozen environment is passed.
    """
    monkeypatch.setattr(_ci_summary.platform, "python_version", lambda: "9.99.99-leak")
    monkeypatch.setattr(_ci_summary.platform, "platform", lambda: "FakeOS-Quantum-Leak")
    monkeypatch.setattr(_ci_summary, "_short_git_sha", lambda _root: "deadbee")
    monkeypatch.setattr(_ci_summary, "_package_version", lambda _name: "0.0.0-leak")
    # Wall-clock leak guard: if any code path bypasses ``env.now_utc`` and
    # calls ``_utc_now()`` directly, the rendered "Change Since Last Run" age
    # would jump from "1 day ago" to "5000 days ago" and break byte-identity.
    monkeypatch.setattr(
        _ci_summary,
        "_utc_now",
        lambda: datetime(2039, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
    )
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://leak.invalid")
    monkeypatch.setenv("GITHUB_REPOSITORY", "leak/leak")
    monkeypatch.setenv("GITHUB_RUN_ID", "999999999")

    fixt = _FIXTURES_DIR / "system_tests_full_conformance"
    data = _parse(fixt / "pytest.xml")
    cu_payload = _load_json(fixt / "cu_results.json")
    baseline = _load_baseline(fixt / "baseline.json") if (fixt / "baseline.json").exists() else None

    produced, _context = render_conformance_summary(
        data,
        FIXED_SERVER_URL,
        FIXED_RUN_TS,
        cu_payload,
        baseline,
        report_environment=FROZEN_ENV,
    )

    expected = (_EXPECTED_DIR / "system_tests_full_conformance.md").read_text(encoding="utf-8")
    assert produced == expected, (
        "Renderer leaked a live-environment read into byte-identity output. "
        "Every runtime-derived value must come from the passed ReportEnvironment, "
        "not from `platform.*`, `_short_git_sha`, `_package_version`, or `GITHUB_*` env vars."
    )
    # Belt-and-braces: the leaked sentinels must never appear in the output.
    for sentinel in ("9.99.99-leak", "FakeOS-Quantum-Leak", "deadbee", "0.0.0-leak", "leak.invalid"):
        assert sentinel not in produced, f"Leaked sentinel {sentinel!r} found in renderer output"
    assert "5000 days ago" not in produced and "9000 days ago" not in produced, (
        "Renderer leaked a wall-clock read into byte-identity output. "
        "All age calculations must come from `env.now_utc`, not `_utc_now()` or `datetime.now()`."
    )


def test_failure_overflow_row_uses_explicit_wording() -> None:
    """Failure overflow rows must not use ellipsis placeholders."""
    data = {
        "passed": 0,
        "failed": 31,
        "errors": 0,
        "skipped": 0,
        "xfailed": 0,
        "total": 31,
        "duration_s": 1,
        "failures": [{"name": f"test_failure_{index}", "message": "boom"} for index in range(31)],
        "skip_reasons": {},
        "xfail_reasons": {},
    }

    produced, _context = render_conformance_summary(
        data,
        FIXED_SERVER_URL,
        FIXED_RUN_TS,
        cu_payload=None,
        baseline=None,
        report_environment=FROZEN_ENV,
    )

    assert "| Additional rows | 1 additional failure item(s) are listed in full in `report.xlsx` |" in produced
    assert "| … |" not in produced
    assert "more — see report.xlsx" not in produced


def test_runtime_report_environment_reads_live_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Companion guard: ``ReportEnvironment.from_runtime()`` reads live state.

    Production callers pass ``report_environment=None`` and rely on
    :meth:`ReportEnvironment.from_runtime` to capture live values. This test
    proves that constructor reads the patched values back, so production
    reports keep showing the actual Python version, OS, asyncua release, git
    SHA, and GitHub Actions run URL.
    """
    monkeypatch.setattr(_ci_summary.platform, "python_version", lambda: "3.99.0-test")
    monkeypatch.setattr(_ci_summary.platform, "platform", lambda: "TestOS-1.0")
    monkeypatch.setattr(_ci_summary, "_short_git_sha", lambda _root: "abc1234")
    monkeypatch.setattr(_ci_summary, "_package_version", lambda _name: "9.9.9-test")
    fixed_now = datetime(2027, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    monkeypatch.setattr(_ci_summary, "_utc_now", lambda: fixed_now)
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://example.test")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_RUN_ID", "42")

    env = ReportEnvironment.from_runtime()
    assert env.git_sha == "abc1234"
    assert env.python_version == "3.99.0-test"
    assert env.asyncua_version == "9.9.9-test"
    assert env.host_os == "TestOS-1.0"
    assert env.run_logs_url == "https://example.test/owner/repo/actions/runs/42"
    assert env.now_utc == fixed_now
    assert env.repro_command == "python run_all_tests.py"


def test_cell_width_handles_report_icons() -> None:
    assert _ci_summary._cell_width("⏭️") == 2
    assert _ci_summary._cell_width("✅") == 2
    assert _ci_summary._cell_width("❌") == 2
    assert _ci_summary._cell_width("⚠️") == 2
    assert _ci_summary._cell_width("⚪") == 2
    assert _ci_summary._cell_width("⚙️") == 2
    assert _ci_summary._cell_width("⏱️") == 2
    assert _ci_summary._cell_width("ℹ️") == 2
    assert _ci_summary._cell_width("🚦") == 2
    assert _ci_summary._cell_width("🧮") == 2
    assert _ci_summary._cell_width("🛠️") == 2
    assert _ci_summary._cell_width("🟢") == 2
    assert _ci_summary._cell_width("🔴") == 2
    assert _ci_summary._cell_width("🟠") == 2
    assert _ci_summary._cell_width("abc") == 3
    assert _ci_summary._cell_width("Passed") == 6
    assert _ci_summary._cell_width("Partially Supported") == 19
