# IJT Test Client — Specification Test Summary Renderer

## What this package is

`reporting/specification_test_summary.py` renders the **IJT Test Client specification test
report** that is uploaded as `test-results/summary.md` and surfaced on the
GitHub Actions run page during the nightly System Tests workflow.

Inputs:

- `test-results/pytest.xml` — the specification test pytest run.
- `test-results/cu-coverage-report.json` — per-CU outcomes produced by the
  Test Client specification test run.

Output: a single Markdown document containing _Specification Test Overview_, _Capability
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
  specification test step in `integration.yml` calls
  `python scripts/make_specification_test_summary.py`.

In other words, this package is **specification-test-only**, and that matches
the Test Client's charter (profiles, capability units, and explicit validation
and server-support metrics). Repository-wide CI and System Tests reporting is
a separate concern, owned by the reporting maintainers, and lives outside
this package.

## File layout

```
scripts/
├── make_specification_test_summary.py # CLI shim (parses args, reads files, calls renderer, writes outputs)
└── reporting/
    ├── __init__.py
    ├── specification_test_summary.py  # Pure renderer: render_specification_test_summary(...)
    └── README.md               # this file
```

The shim `make_specification_test_summary.py` is invoked only from
`.github/workflows/integration.yml` (the Test Client live specification test step),
never from `ci.yml`. The name reflects that this package produces the Test
Client specification test summary and nothing else.

## Ownership

Test Client specification test maintainers. Any change to wording, headings,
column meaning, or scoring must:

1. Go through `docs/REPORT_GLOSSARY.md` (the authoritative in-repo
   terminology reference).
2. Update or regenerate the byte-identity expected fixtures under
   `tests/unit/reporting/fixtures/expected/` only when the change is
   intentional and reviewed.
