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
2. Calls ``render_conformance_summary(...)`` with frozen ``run_ts`` and
   ``server_url`` so wall-clock time and environment cannot drift the
   output.
3. Asserts byte-equality against the corresponding expected Markdown
   under ``fixtures/expected/``.

To intentionally regenerate the expected files (review the diff before
landing), run ``python tests/unit/reporting/_capture_expected_summaries.py``
from the IJT_Test_Client directory.
"""

from __future__ import annotations

import sys
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

from make_conformance_summary import _load_baseline, _load_json, _parse  # noqa: E402
from reporting.conformance_summary import render_conformance_summary  # noqa: E402

FIXED_RUN_TS = "2026-05-13 14:00 UTC"
FIXED_SERVER_URL = "opc.tcp://fixture.ijt.test:40451"
# Frozen build metadata: matches the captured expected fixtures so the
# byte-identity test stays deterministic regardless of the local git SHA
# or the ``GITHUB_*`` environment variables present during the run. Must
# stay in sync with ``_capture_expected_summaries.py``.
FIXED_GIT_SHA = "15bc900"
FIXED_RUN_LOGS_URL = "n/a"

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
        git_sha=FIXED_GIT_SHA,
        run_logs_url=FIXED_RUN_LOGS_URL,
    )

    expected = (_EXPECTED_DIR / expected_file).read_text(encoding="utf-8")
    assert produced == expected, (
        f"Renderer output drifted from {expected_file}. "
        "If this change is intentional, regenerate expected files with "
        "`python tests/unit/reporting/_capture_expected_summaries.py` "
        "and review the diff."
    )
