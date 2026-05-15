# IJT Test Client — Conformance Summary Renderer

## What this package is

`reporting/conformance_summary.py` renders the **IJT Test Client conformance
report** that is uploaded as `test-results/summary.md` and surfaced on the
GitHub Actions run page during the nightly System Tests workflow.

Inputs:

- `test-results/pytest.xml` — the conformance pytest run.
- `test-results/cu-compliance-report.json` — per-CU outcomes produced by the
  Test Client conformance run.
- `test-results/report-baseline.json` — the previous run's baseline for the
  "Change Since Last Run" block (optional).

Output: a single Markdown document containing _Conformance Overview_, _Capability
Support_, _Action Items_, _Informational Notes_, _Coverage Overview_, _Facet
and CU Coverage_, _Conformance Status_, _Full CU Coverage_, _Test Environment_,
_Change Since Last Run_, etc.

## What this package is **not**

- It is **not** the repository-wide CI summary table. That table
  ("IJT OPC UA — CI") is generated inline by Python embedded in
  `.github/workflows/ci.yml` (see job `report` → step
  `Generate Summary Table`).
- It is **not** the repository-wide System Tests summary table. That table
  ("IJT OPC UA — Integration") is generated inline by Python embedded in
  `.github/workflows/integration.yml` (same job/step name).
- It is **not** invoked from `ci.yml`. Only the Test Client live
  conformance step in `integration.yml` calls
  `python scripts/make_conformance_summary.py`.

In other words, this package is **conformance-only**, and that matches
the Test Client's charter (profiles, capability units, and conformance
scoring). Repository-wide CI/System Tests reporting is a separate concern
and is scheduled for Phase 1B of the reporting overhaul, where those inline
generators will be lifted out of YAML into their own top-level package
(likely `scripts/reporting/` at the repo root, owned by the reporting
maintainers, not the Test Client).

## File layout

```
scripts/
├── make_conformance_summary.py # CLI shim (parses args, reads files, calls renderer, writes outputs)
└── reporting/
    ├── __init__.py
    ├── conformance_summary.py  # Pure renderer: render_conformance_summary(...)
    └── README.md               # this file
```

The shim was previously named `make_ci_summary.py` — a misleading name that
predated the split between Test-Client conformance reporting and repo-wide
CI reporting. It is invoked only from `.github/workflows/integration.yml`
(the Test Client live conformance step), never from `ci.yml`. The rename
to `make_conformance_summary.py` was bundled into the Phase 1 renderer
extraction commit so the file's name and its purpose stay consistent.

## Ownership

Test Client conformance maintainers. Any change to wording, headings,
column meaning, or scoring must:

1. Go through `docs/REPORT_GLOSSARY.md` (the authoritative in-repo
   terminology reference).
2. Update or regenerate the byte-identity expected fixtures under
   `tests/unit/reporting/fixtures/expected/` only when the change is
   intentional and reviewed.
