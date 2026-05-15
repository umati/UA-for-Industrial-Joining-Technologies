# IJT Report Glossary and Reading Guide

**Status:** authoritative in-repo terminology reference for the IJT Test
Client conformance summary renderer
(`scripts/reporting/conformance_summary.py`) and the Excel parity report
(`scripts/make_excel_report.py`).

**Audience tags:** 👔 management - 🛠 dev - 🧪 test - 📦 customer

This glossary defines every term that appears in:
- the Test Client conformance summary (`scripts/reporting/conformance_summary.py`,
 invoked via `scripts/make_conformance_summary.py` from
 `.github/workflows/integration.yml`)
- the repo-wide CI summary table (inline Python in
 `.github/workflows/ci.yml` job `report`; will move to its own module in
 Phase 1B)
- the Excel parity report (`scripts/make_excel_report.py`)
- the workflow display names and Checks tab

Source citations below identify code by **symbol** (function, constant,
section heading, or unique header string) rather than line number, so they
stay valid as code moves. If a cited symbol is renamed or removed, treat
it as a glossary bug and fix it in the same PR that touches the symbol.

---

## 1. Workflow names (top of run page) 👔 🛠️ 🧪 📦

| Current display name | Source anchor | What it means |
|---|---|---|
| `CI — Fast Checks` | `.github/workflows/ci.yml` (`name:` field) | Pull-request fast gate for builds, unit tests, lint, vulnerability scan, and required Docker checks. |
| `System Tests — Live OPC UA, Browser, Docker, Conformance` | `.github/workflows/integration.yml` (`name:` field) | Nightly + manual full system run against live OPC UA server, browser end-to-end suites, Docker compose, and conformance harness. |
| `Security — CodeQL` | `.github/workflows/codeql.yml` (`name:` field) | GitHub native code scanning. Matrix job names `Analyze (javascript)`, `Analyze (csharp)`, and `Analyze (python)` stay unchanged because ruleset `15294123` requires those contexts. |
| `Web Client — Browser Compatibility Smoke` | `.github/workflows/web-client-compatibility-smoke.yml` (`name:` field) | Scheduled/manual browser smoke for audited Web Client file surfaces. The issue key `[Web Client Compatibility Smoke]` stays unchanged for continuity. |

> 👔 management: the names describe the purpose of the run. Required branch-protection contexts are governed by the GitHub ruleset, not by these display labels.

---

## 1.1 Summary chart color contract

| Visual meaning | Mermaid binding | Color |
|---|---|---|
| Pass / completed | `pie1`, `doneTaskBkgColor` | Green `#22c55e` |
| Failure / current bottleneck | `pie2`, `critBkgColor` | Red `#ef4444` |
| Skipped / neutral | `pie3`, `taskBkgColor` | Gray `#9ca3af` |

---

## 2. Conformance report top-level terms

### 2.1 `Conformance Overview` 👔 🛠️ 🧪 📦
Source: `scripts/reporting/conformance_summary.py` (`## Conformance Overview` heading and KPI table emitted in `render_conformance_summary()`).
Rendered as a **three-column KPI strip** (`Server Support Coverage` | `Validation Health` | `CU Status`) **plus a three-cell context row** beneath it.

The `CU Status` cell renders the four KPI labels defined by `KPI_LABELS` in `helpers/report_scoring.py`: **`Failed` · `Blocked` · `Not Supported` · `With Notes`** (no `Supported` count in this strip; `format_kpi_strip()` in `helpers/report_scoring.py` only emits the four KPI labels).

**Why renamed:** the old "At a Glance" wording was informal; non-IJT readers (management, customers) parsed it as "look here for everything," not "high-level KPIs." `Conformance Overview` says exactly what the block contains.

### 2.2 `Server Support Coverage` 👔 🛠️ 📦
Source: `scripts/reporting/conformance_summary.py` — `Server Support Coverage` column header in the `## Conformance Overview` KPI table; value is the local `spec_coverage_value` computed in `render_conformance_summary()`.
The share of OPC 40100 Joining Test Result CUs (Conformance Units) that the **server under test claims to support** in its capability file.
- **Numerator:** CUs the server lists as supported.
- **Denominator:** CUs in the active profile (facet or full set).
- Example: 78% means the server says it supports 78% of the CUs in the active profile.
**Why renamed:** "Spec Coverage" suggested test coverage of the spec, which it is not. The value is about **what the server says it supports**, not what the tests cover.

### 2.3 `Validation Health` 👔 🛠️ 🧪 📦
Source: `scripts/reporting/conformance_summary.py` — `Validation Health` column header in the `## Conformance Overview` KPI table; value is the local `validation_health_value` computed in `render_conformance_summary()` via `_supported_cus_validated_pct_value()`.
The share of server-supported CUs that this run validated as **Supported** or **Supported with Notes**.
- **Numerator:** CUs validated as Supported or Supported with Notes.
- **Denominator:** CUs the server says it supports.
- Example: 95% means 95% of the CUs the server claims to support were proven by tests.
**Note:** Formula stays as-is. Any future weighting change requires a separate proposal document and PR.

### 2.4 `CU Status` (label unchanged) 👔 🛠️ 🧪 📦
Source: `scripts/reporting/conformance_summary.py` — `CU Status` column header in the `## Conformance Overview` KPI table; strip rendered via `_format_kpi_strip(findings_count)` (the `findings_count` Counter is built in `render_conformance_summary()`).
Compressed status counts across all CUs. The strip renders the four KPI labels from `KPI_LABELS` in `helpers/report_scoring.py`:

```
Failed · Blocked · Not Supported · With Notes
```

There is **no `Supported` count in this strip** — the strip only highlights the four buckets that need attention.

There is no formula change and no new bucket. The internal JSON key remains `action_needed`; the public report label is `Failed`.

### 2.5 Score 🛠️ 🧪
Source: formula lives in `conformance_score()` in `helpers/report_scoring.py`; called as `_conformance_score(...)` inside `render_conformance_summary()` in `scripts/reporting/conformance_summary.py`; rendered as the `**Score: …**` banner emitted by the same function.
0–100 composite, currently `0.7 × Validation Health + 0.3 × Server Support Coverage`,
capped at 50 if any internal `action_needed` / public **Failed** item exists, capped at 75 if any **Blocked** item exists.
**Note on taxonomy:** the internal source term is still `action_needed`; the public report label is `Failed`.

---

## 3. Outcome / status terms

### 3.1 `Review Status` and `Outcome` 🛠️ 🧪
The report deliberately keeps two concepts:
- `Review Status` highlights follow-up work for the reader (`Failed`, `Blocked`, `Not Supported`, `With Notes`).
- `Outcome` is the CU-level conformance classification for the current run.

Current table shapes:
- Compact review table: `Review Status | CU | Outcome | Primary Reason | Δ`.
- `Conformance Status` collapsed `<details>` table: includes `Review Status`, `Outcome`, and `Failures`.
- `Full CU Coverage` collapsed `<details>` table: includes `Outcome` and `Failures` (no `Review Status` column).
- Coverage aggregate tables may show `Outcomes | Outcome`: `Outcomes` is the aggregate count column, while `Outcome` is the per-row classification.

| Outcome | Icon | Meaning | Internal source term | Source |
|---|---|---|---|---|
| Supported | ✅ | Test validated this CU as supported. | `Supported` | `OUTCOME_LABELS["supported"]` in `helpers/report_scoring.py` |
| Supported with Notes | ⚠ | Validated but with caveats (e.g., partial coverage). Mapped from `partial` key. | `Supported with Notes` (KPI strip uses short form `With Notes` from `KPI_LABELS`) | `OUTCOME_LABELS["partial"]`, `KPI_LABELS` in `helpers/report_scoring.py` |
| Not Supported | ➖ | Server-supported CU was not validated as supported by this run. | `Not Supported` | `OUTCOME_LABELS["not_supported"]` in `helpers/report_scoring.py` |
| Blocked | 🚫 | Missing runtime precondition (e.g., dependency CU failed). | `Blocked` | `OUTCOME_LABELS["blocked"]` in `helpers/report_scoring.py` |
| Failed | ❌ | Test failure or harness/runtime error. | `action_needed` | `OUTCOME_LABELS["action_needed"]`, `ACTION_ITEM_LABEL_ORDER` in `helpers/report_scoring.py` |

The internal JSON key remains `action_needed` so existing machine-readable data stays stable. The public label is `Failed`.

### 3.2 `Failures` 🛠️ 🧪
Source: `scripts/reporting/conformance_summary.py` — `Failures` column header in both the `Conformance Status` and `Full CU Coverage` collapsed `<details>` tables; Excel parity in the `Failures` column emitted by `make_excel_report.py`.
The single count of failures and harness/runtime errors. The code already collapses these into one number; the column name now matches the existing Excel sheet name `Failures` built by `_build_filtered(..., "Failures", ...)` in `make_excel_report.py`.

> Note: The column `Failures` counts pytest `failed + errors`. The CU **outcome** label `Failed` is not the same field: `Failures` is a per-CU count of underlying test failures+errors; `Failed` is the CU-level outcome bucket.

---

## 4. Coverage and capability terms

### 4.1 `Facet and CU Coverage` 🛠️ 🧪
Source: `scripts/reporting/conformance_summary.py` — `Facet and CU Coverage` `<details>` block; full capability-area details are emitted by `_render_supports_block()`.
The table of facet-level rows that breaks down validation by facet of the OPC 40100 IJT profile, plus the Reference IJT facet and Reference full CU set rows.
**Why renamed:** the table contains both facets and CU-level rows; the old name hid the CU rows.

### 4.2 `Capability Notes` (label kept) 🛠️ 🧪
Source: `scripts/reporting/conformance_summary.py` — `## Capability Notes` section in `_render_review_sections()`; filter uses `_CAPABILITY_NOTE_LABELS` (= {Not Supported, Supported with Notes}, imported from `helpers/report_scoring.py`).
Per-CU notes about CUs that are **not** action items (no failure, no block) but still need explanation.
**Why kept (not renamed to `Exceptions`):** "Exception" has a specific meaning in the OPC UA spec (StatusCode-bearing condition); reusing that term in the report would be confusing.

### 4.3 `Coverage Overview` (label kept) 👔 🛠️ 🧪 📦
Source: `scripts/reporting/conformance_summary.py` section heading.
A small table summarizing how much of the active profile each row covered. Numbers are independent of pass/fail; they express **breadth**, not **success**.

### 4.4 `Full CU Coverage` (label kept) 🛠️ 🧪
Source: `scripts/reporting/conformance_summary.py` collapsed `<details>` block.
The full list of every CU in the active profile with its individual outcome.

### 4.5 `Skip Diagnostics` 🛠️ 🧪
Source: `scripts/reporting/conformance_summary.py` section heading.
Skip-reason histogram for diagnostic purposes only. Skip counts here **overlap** with CU outcomes above and should not be added to them.

---

## 5. Document structure terms

### 5.1 `Glossary and Reading Guide` 👔 🛠️ 🧪 📦
Source: `scripts/reporting/conformance_summary.py` section heading.
The trailing section that defines terms inline inside the generated report. This file is the authoritative in-repo terminology reference.

### 5.2 `Conformance Status` (label kept) 🛠️ 🧪
Source: `scripts/reporting/conformance_summary.py` collapsed `<details>` block heading.
The detail table of action items and capability notes that need explanation.

### 5.3 `Since Last Run` (block) 🛠️ 🧪
Source: baseline read by `_load_baseline()` in `scripts/make_conformance_summary.py`; Δ-block emitted by `_render_delta_block()` in `scripts/reporting/conformance_summary.py`; baseline payload built by `_baseline_payload()` in `scripts/reporting/conformance_summary.py`; baseline write by `_write_baseline()` in `scripts/make_conformance_summary.py` (invoked from `main()`).
Comparison with the previously persisted `test-results/report-baseline.json`.
When no baseline exists, the block is **hidden**, not shown with an empty message.

---

## 6. Timing diagnostics terms

### 6.1 `Bottleneck Spotlight` (new in Phase 3) 🛠️ 🧪
Auto-detects the slowest current job/suite and shows the top-5 slowest tests in that suite. Replaces the hardcoded "Top C# Live Tests" section.
**Why auto:** the longest pole changes over time (Phase 3 Q15). Hardcoding "C# Live Tests" hid Web Client regressions when they became slower than C#.

### 6.2 Timing layers (Phase 3) 🛠️ 🧪
- **Layer 1 (always visible):** Mermaid gantt of all job durations.
- **Layer 2 (always visible):** `Bottleneck Spotlight`.
- **Layer 3 (`<details>` collapsed):** per-suite top-5 for every suite with wall time > 60s.

---

## 7. Cross-report parity (Markdown ↔ Excel) 🛠️ 🧪
- Every term rendered in `scripts/reporting/conformance_summary.py` is rendered in lockstep in `make_excel_report.py`.
- Excel sheet `Failures` is the canonical name and is preserved (`_build_filtered(..., "Failures", ...)` in `make_excel_report.py`).
- Excel terminology source: column-header constants and sheet builders in `scripts/make_excel_report.py`.

---

## 8. Out of scope for this glossary
- Tier definitions (`docs/TEST_TIERS.md`). The stale C# skip-count claim was fixed in Phase 7.
- Internal-only Python identifiers (`_ACTION_ITEM_LABEL_ORDER`, etc.) — these are implementation details and not user-facing.
- CI/CD plumbing terms not appearing in the rendered report.

---

## 9. Internal implementation terms

The source data still uses the internal discriminator **`rollup`** for grouped
facet definitions. The renderer and Excel workbook expose those rows as
**`Facet Group`**.

Internal Python (`kind == "rollup"` discriminator, `rollups` list variable) may
stay as-is because it is not user-visible.
