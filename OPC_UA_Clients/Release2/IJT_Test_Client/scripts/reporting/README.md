# IJT Test Client — Conformance Summary Renderer

## What this package is

`reporting/conformance_summary.py` renders the **IJT Test Client conformance
report** that is uploaded as `test-results/summary.md` and surfaced on the
GitHub Actions run page during the nightly System Tests workflow.

Inputs:

- `test-results/pytest.xml` — the conformance pytest run.
- `test-results/cu-compliance-report.json` — per-CU outcomes produced by the
  Test Client conformance run.

Output: a single Markdown document containing _Conformance Overview_, _Capability
Support_, _Action Items_ when there are failed or blocked CUs, _Scope Notes_,
_Facet Breakdown_, _CU Detail_, _Diagnostics_, etc.

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
the Test Client's charter (profiles, capability units, and explicit validation
and server-support metrics). Repository-wide CI and System Tests reporting is
a separate concern, owned by the reporting maintainers, and lives outside
this package.

## File layout

```
scripts/
├── make_conformance_summary.py # CLI shim (parses args, reads files, calls renderer, writes outputs)
└── reporting/
    ├── __init__.py
    ├── conformance_summary.py  # Pure renderer: render_conformance_summary(...)
    └── README.md               # this file
```

The shim `make_conformance_summary.py` is invoked only from
`.github/workflows/integration.yml` (the Test Client live conformance step),
never from `ci.yml`. The name reflects that this package produces the Test
Client conformance summary and nothing else.

## Ownership

Test Client conformance maintainers. Any change to wording, headings,
column meaning, or scoring must:

1. Go through `docs/REPORT_GLOSSARY.md` (the authoritative in-repo
   terminology reference).
2. Update or regenerate the byte-identity expected fixtures under
   `tests/unit/reporting/fixtures/expected/` only when the change is
   intentional and reviewed.
