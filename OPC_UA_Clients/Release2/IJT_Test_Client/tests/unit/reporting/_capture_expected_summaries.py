"""Maintenance helper: regenerate the expected conformance summary Markdown.

Run from the IJT_Test_Client/ directory:

    python tests/unit/reporting/_capture_expected_summaries.py

For each fixture under ``tests/unit/reporting/fixtures/``, this re-runs the
current conformance renderer (``scripts/reporting/conformance_summary.py``)
with frozen inputs (no wall-clock time, no baseline file write, no live
environment reads) and overwrites the corresponding expected Markdown file
under ``tests/unit/reporting/fixtures/expected/``.

Only re-run this helper when the renderer output is intentionally allowed
to change. The byte-equality test in ``test_render_conformance_summary.py``
otherwise acts as the regression gate.
"""

from __future__ import annotations

import sys
from pathlib import Path

# scripts/ is not a Python package; add it to sys.path so we can import the
# renderer the same way the workflow CLI does (``python
# scripts/make_conformance_summary.py`` puts scripts/ on sys.path[0]).
_SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# Sibling helper modules (``_frozen_env``) live next to this script in a
# non-package directory; ensure they're importable when this helper is run
# directly as ``python tests/unit/reporting/_capture_expected_summaries.py``.
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from _frozen_env import FIXED_RUN_TS, FIXED_SERVER_URL, FROZEN_ENV  # noqa: E402
from make_conformance_summary import _load_baseline, _load_json, _parse  # noqa: E402
from reporting.conformance_summary import render_conformance_summary  # noqa: E402

FIXTURES_DIR = Path(__file__).parent / "fixtures"
EXPECTED_DIR = FIXTURES_DIR / "expected"

CASES = [
    ("ci_unit_no_cu_payload", "ci_unit_no_cu_payload.md"),
    ("system_tests_full_conformance", "system_tests_full_conformance.md"),
]


def render_fixture(fixture_dir: Path) -> str:
    data = _parse(fixture_dir / "pytest.xml")
    cu_json = fixture_dir / "cu_results.json"
    baseline_json = fixture_dir / "baseline.json"
    cu_payload = _load_json(cu_json) if cu_json.exists() else None
    baseline = _load_baseline(baseline_json) if baseline_json.exists() else None
    md, _ctx = render_conformance_summary(
        data,
        FIXED_SERVER_URL,
        FIXED_RUN_TS,
        cu_payload=cu_payload,
        baseline=baseline,
        report_environment=FROZEN_ENV,
    )
    return md


def main() -> int:
    EXPECTED_DIR.mkdir(parents=True, exist_ok=True)
    for fixture_name, expected_name in CASES:
        md = render_fixture(FIXTURES_DIR / fixture_name)
        out = EXPECTED_DIR / expected_name
        out.write_text(md, encoding="utf-8", newline="\n")
        print(f"wrote {out} ({len(md)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
