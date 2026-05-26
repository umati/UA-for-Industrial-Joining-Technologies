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
- the repo-wide CI summary table (`reporting/ci_run_summary.py`, invoked by
 `.github/workflows/ci.yml` job `report`)
- the System Tests summary (`reporting/system_tests_run_summary.py`, invoked by
 `.github/workflows/integration.yml`)
- the Excel parity report (`scripts/make_excel_report.py`)
- the workflow display names and Checks tab

Source citations below identify code by **symbol** (function, constant,
section heading, or unique header string) rather than line number, so they
stay valid as code moves. Citations are part of the glossary contract: if a
cited symbol moves, the glossary entry moves with it.

---

## 1. Workflow names (top of run page) 👔 🛠️ 🧪 📦

| Current display name | Source anchor | What it means |
|---|---|---|
| `CI — Unit, Static, and Smoke Gates` | `.github/workflows/ci.yml` (`name:` field) | Pull-request gate for unit suites, static analysis, vulnerability scans, and required smoke checks. |
| `System Tests — Live OPC UA, Browser, Docker, Conformance` | `.github/workflows/integration.yml` (`name:` field) | Nightly + manual full system run against live OPC UA server, browser end-to-end suites, Docker compose, and conformance harness. |
| `Security — CodeQL` | `.github/workflows/codeql.yml` (`name:` field) | GitHub native code scanning. Matrix job names `Analyze (javascript)`, `Analyze (csharp)`, and `Analyze (python)` stay unchanged because ruleset `15294123` requires those contexts. |
| `Web Client — Browser Compatibility Smoke` | `.github/workflows/web-client-compatibility-smoke.yml` (`name:` field) | Scheduled/manual browser smoke for audited Web Client file surfaces. The issue key `[Web Client Compatibility Smoke]` stays unchanged for continuity. |

> 👔 management: the names describe the purpose of the run. Required branch-protection contexts are governed by the GitHub ruleset, not by these display labels.

---

## 1.1 Summary status marker contract

| Visual meaning | Report marker | Notes |
|---|---|---|
| Pass / completed | `✅` | Successful gate, check, or validated outcome. |
| Failure | `❌` | Failed gate, check, or CU outcome. |
| Current bottleneck | `🏁` | Longest reliable timing source in the current run. |
| Skipped / neutral | `⏭️` / `⚪` | Skipped lane/check or neutral capability-scope fact. |

---

## 2. Conformance report top-level terms

### 2.1 `📊 Conformance Overview` 👔 🛠️ 🧪 📦
Source: `scripts/reporting/conformance_summary.py` (`## 📊 Conformance Overview` heading and KPI table emitted in `render_conformance_summary()`).
Rendered as a **four-column KPI strip** (`Server Support Coverage` | `Validation Health` | `Conformance Action Items` | `Server Scope Notes`) **plus a four-cell context row** beneath it. All KPI labels are plain text.

`Conformance Action Items` renders **`Failed` · `Blocked`** and means work to investigate or fix. `Server Scope Notes` renders **`Not Supported` · `With Notes`** and means capability gaps or caveats for context.

The IJT Facet Support full table splits the support icon into its own `🚦` column, and the IJT Facet Support and Conformance Overview sections include one-line legends for the support and review icon meanings.

### 2.2 `Server Support Coverage` 👔 🛠️ 📦
Source: `scripts/reporting/conformance_summary.py` — `Server Support Coverage` column header in the `## 📊 Conformance Overview` KPI table; value is the local `spec_coverage_value` computed in `render_conformance_summary()`.
The share of OPC 40100 Joining Test Result CUs (Conformance Units) that the **server under test claims to support** in its capability file.
- **Numerator:** CUs the server lists as supported.
- **Denominator:** CUs in the active profile (facet or full set).
- Example: 78% means the server says it supports 78% of the CUs in the active profile.

### 2.3 `Validation Health` 👔 🛠️ 🧪 📦
Source: `scripts/reporting/conformance_summary.py` — `Validation Health` column header in the `## 📊 Conformance Overview` KPI table; value is the local `validation_health_value` computed in `render_conformance_summary()` via `_supported_cus_validated_pct_value()`.
The share of server-supported CUs that this run validated as **Supported** or **Supported with Notes**.
- **Numerator:** CUs validated as Supported or Supported with Notes.
- **Denominator:** CUs the server says it supports.
- Example: 95% means 95% of the CUs the server claims to support were proven by tests.

### 2.4 `Conformance Action Items` and `Server Scope Notes` 👔 🛠️ 🧪 📦
Source: `scripts/reporting/conformance_summary.py` — `Conformance Action Items` and `Server Scope Notes` column headers in the `## 📊 Conformance Overview` KPI table; cells rendered via `_format_status_counts(...)` from `helpers/report_scoring.py` (the `findings_count` Counter is built in `render_conformance_summary()`).
Compressed status counts across all CUs. The split renders the four KPI labels from `KPI_LABELS` in `helpers/report_scoring.py` as two reader layers:

```
Conformance Action Items: Failed · Blocked
Server Scope Notes:       Not Supported · With Notes
```

There is **no `Supported` count in these cells** — they only highlight buckets that need follow-up or explanation.

There is no formula change and no new bucket. The internal JSON key remains `action_needed`; the public report label is `Failed`.

### 2.5 Baseline score field 🛠️ 🧪
Source: formula lives in `conformance_score()` in `helpers/report_scoring.py`; called as `_conformance_score(...)` while building the report context.
The 0–100 composite is an internal-only trend field written to `test-results/report-baseline.json`. It is not rendered as a public compliance grade. Public summaries use the explicit `Validation Health` and `Server Support Coverage` metrics instead.
**Taxonomy:** the internal source key is `action_needed`; the public report label is `Failed`.

---

## 3. Outcome / status terms

### 3.1 `Review Status` and `Outcome` 🛠️ 🧪
The report deliberately keeps two concepts:
- `Review Status` highlights follow-up work for the reader (`Failed`, `Blocked`, `Not Supported`, `With Notes`).
- `Outcome` is the CU-level conformance classification for the current run.

Current table shapes:
- `Conformance Unit Details` collapsed `<details>` table: includes `Review Status`, `Outcome`, `Primary Reason`, test counts, and workbook case counts.
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
Source: `scripts/reporting/conformance_summary.py` — `Failures` column header in the `Conformance Unit Details` collapsed `<details>` table; Excel parity in the `Failures` column emitted by `make_excel_report.py`.
The single count of failures and harness/runtime errors. The code already collapses these into one number; the column name matches the column header used by `_build_filtered(..., "Test Failures", ...)` in `make_excel_report.py`.

> Note: The column `Failures` counts pytest `failed + errors`. The CU **outcome** label `Failed` is not the same field: `Failures` is a per-CU count of underlying test failures+errors; `Failed` is the CU-level outcome bucket.

---

## 4. Coverage and capability terms

> **Naming parity:** the markdown report and the Excel workbook now share the
> same vocabulary. The markdown sections (`IJT Facet Breakdown`,
> `Server Scope Notes`, `Conformance Unit Details`,
> `Skip & Expected-Failure Diagnostics`) are mirrored 1:1 by the Excel sheet
> tabs (`IJT Facet Breakdown`, `Conformance Unit Details`,
> `Profile Coverage Comparison`, …). See the
> [Workbook Sheets](#workbook-sheets) and
> [Markdown Sections](#markdown-sections) tables below.

### 4.1 `IJT Facet Breakdown` 🛠️ 🧪
Source: `scripts/reporting/conformance_summary.py` — `## 📐 IJT Facet Breakdown`; full IJT facet details are emitted by `_render_supports_block()`. The Excel workbook mirrors this as the `IJT Facet Breakdown` sheet built by `_build_facet_coverage(...)` in `make_excel_report.py`.
The table of facet-level rows that breaks down validation by IJT Companion Spec facet of the OPC 40100 profile.

### 4.2 `Server Scope Notes` 🛠️ 🧪
Source: `scripts/reporting/conformance_summary.py` — `## 📝 Server Scope Notes` section in `_render_review_sections()`; filter uses `_CAPABILITY_NOTE_LABELS` (= {Not Supported, Supported with Notes}, imported from `helpers/report_scoring.py`).
Per-CU notes about CUs that are **not** action items (no failure, no block) but still need explanation. The label deliberately avoids `Exceptions`, because "Exception" has a specific meaning in the OPC UA spec (a StatusCode-bearing condition) and reusing that term in the report would be confusing.

### 4.3 `Profile Coverage Comparison` 👔 🛠️ 🧪 📦
Excel-only sheet built by `_build_profile_coverage(...)` in `make_excel_report.py`. It compares the active profile against the server's declared capability set, surfacing per-profile CU totals, supported counts, and outcomes side by side. The markdown report intentionally omits this comparison because the same numbers are already covered by the KPI strip and the facet rows; the sheet exists as a deep-dive lens for Excel readers.

### 4.4 `Conformance Unit Details` 🛠️ 🧪
Source: `scripts/reporting/conformance_summary.py` collapsed `<details>` block (`## 📋 Conformance Unit Details`); Excel parity in the `Conformance Unit Details` sheet built by `_build_cu_coverage(...)` in `make_excel_report.py`.
The full list of every CU with its individual outcome, review status, primary reason, and test/workbook counts.

### 4.5 `Skip & Expected-Failure Diagnostics` 🛠️ 🧪
Source: `scripts/reporting/conformance_summary.py` `Skip & Expected-Failure Diagnostics` `<details>` block. Skip-reason and expected-failure histograms for diagnostic purposes only. The markdown view filters out `Not Supported:` reasons because those are already represented in `Conformance Unit Details`; the Excel `Skipped Test Cases` and `Expected Failures` sheets remain raw JUnit evidence.

---

## 5. Document structure terms

### 5.1 Glossary link 👔 🛠️ 🧪 📦
Source: `scripts/reporting/conformance_summary.py` footer.
The generated report links to `docs/REPORT_GLOSSARY.md` instead of repeating the glossary inline. This file is the authoritative in-repo terminology reference.

### 5.2 `Skip & Expected-Failure Diagnostics` 🛠️ 🧪
Source: `scripts/reporting/conformance_summary.py` collapsed `<details>` block heading.
The trailing diagnostics block bundles `Diagnostic Skips` and `Expected Failures` only. The Test Client Environment block ships as a separate `<details>` section, and test outcome counts live exclusively in the Excel `Test Outcome Counts` sheet.

Each run is reported on its own terms; the renderer emits no baseline-driven delta UI. `test-results/report-baseline.json` is written by `_baseline_payload()` as an internal trend artifact only.

---

## 6. Timing diagnostics terms

### 6.1 `⏱️ Performance Benchmarks` 🛠️ 🧪
Compact lane-keyed latency table inside the System Tests Report. Source values are the `perf_*` JUnit `record_property` fields the live perf tests publish (`perf_sample_count`, `perf_mean_total_ms`, `perf_p90_total_ms`, `perf_min_total_ms`, `perf_max_total_ms`, plus optional `perf_threshold_mean_ms` / `perf_threshold_p90_ms`). Loaded by `reporting/system_tests_run_summary.py::load_perf_benchmarks()` and rendered by `render_perf_section()`. The visible table shows first-read min/mean/max latency only; Pass/Fail is derived from `mean < threshold_mean_ms AND perf_p90_total_ms < threshold_p90_ms`, so tail-latency regressions remain gated through the JUnit artifact data without adding a percentile column for end users. The run page no longer receives a separate per-job perf step summary — perf data flows through the aggregator only (see §6.4 for the broader writer-ownership rule).

### 6.2 `Bottleneck Spotlight` 🛠️ 🧪
Auto-detects the slowest current job/suite and appears inside the System Tests `⏱️ Performance Hotspots` section. The detection runs against the current job/suite mix so the slowest lane is always surfaced even as relative timing shifts between Web Client, C# Live, and Test Client lanes.

### 6.3 Timing layers 🛠️ 🧪
- **Layer 1 (always visible):** top timing-source table built from current workflow jobs, Web Browser timing JSON, C# TRX artifacts, and Test Client JUnit durations when available.
- **Layer 2 (always visible):** `Bottleneck Spotlight`.
- **Layer 3 (`<details>` collapsed):** top-10 detail tables for available Web Browser, C# Live, and Test Client Conformance timing artifacts.

### 6.4 Run-page step summary ownership 🛠️ 🧪
Perf, test-result, and Browser CI image summaries for the System Tests workflow are consolidated in the aggregator job (`📋 System Tests Report`); lane jobs (Console Client perf, Test Client perf, Browser CI image resolve, etc.) emit JUnit XML, outputs, and artifacts only and no longer write directly to `$GITHUB_STEP_SUMMARY`. This keeps the run-page summary as a single consolidated block in the audience-tiered order: banner → outcome KPIs → lane results → conformance report → component results → conformance suites → skip details → performance benchmarks → performance hotspots → warnings → artifacts → per-client quick index.

---

## 7. Cross-report parity (Markdown ↔ Excel) 🛠️ 🧪
- Every term rendered in `scripts/reporting/conformance_summary.py` is rendered in lockstep in `make_excel_report.py`.
- Markdown section headings and Excel sheet tab names share the same vocabulary; see the [Workbook Sheets](#workbook-sheets) and [Markdown Sections](#markdown-sections) tables.
- Excel terminology source: column-header constants and sheet builders in `scripts/make_excel_report.py`.

---

<a id="workbook-sheets"></a>

## 7.1 Workbook Sheets 🛠️ 🧪 📦

Locked left-to-right tab order produced by `scripts/make_excel_report.py`:

| # | Sheet tab | Builder | Mirrors markdown section |
|---|---|---|---|
| 1 | `Conformance Overview` | `_build_cover()` | `📊 Conformance Overview` (banner, KPI strip, IJT Facet Support, Server Scope Notes) |
| 2 | `Test Outcome Counts` | `_build_summary()` | Excel-only outcome counts table (markdown omits this — counts live exclusively here) |
| 3 | `IJT Facet Breakdown` | `_build_facet_coverage()` | `📐 IJT Facet Breakdown` |
| 4 | `Conformance Unit Details` | `_build_cu_coverage()` | `📋 Conformance Unit Details` |
| 5 | `Profile Coverage Comparison` | `_build_profile_coverage()` | Excel-only deep-dive comparison |
| 6 | `All Test Cases` | `_build_all_tests()` | Raw evidence backing the markdown report |
| 7 | `Test Failures (N)` | `_build_filtered()` | Failure rows linked from the report `<details>` blocks |
| 8 | `Skipped Test Cases (N)` | `_build_filtered()` | Skip rows backing `Skip & Expected-Failure Diagnostics` |
| 9 | `Expected Failures (N)` | `_build_filtered()` | Xfail/xpass rows backing `Skip & Expected-Failure Diagnostics` |

`(N)` on sheets 7–9 is the matching-row count appended at sheet-creation time by `_build_filtered()` in `scripts/make_excel_report.py` (for example, `Test Failures (3)`).

Sheet tab names mirror the markdown section vocabulary; the workbook is the authoritative artifact and any external automation should bind to these names.

Sheets 3–5 are only emitted when CU JSON is present; the workbook still
produces sheets 1, 2, 6–9 for runs without conformance data.

<a id="markdown-sections"></a>

## 7.2 Markdown Sections 🛠️ 🧪 📦

Top-level sections produced by `scripts/reporting/conformance_summary.py`:

| Heading | Renderer entry point | Workbook mirror |
|---|---|---|
| `# IJT Conformance Test Report` | `render_conformance_summary()` | Workbook banner row (`Conformance Overview` sheet, row 1) |
| `## 📊 Conformance Overview` | `render_conformance_summary()` KPI table | `Conformance Overview` (rows 5–9) |
| `## 🧩 IJT Facet Support` | `_render_supports_block()` | `Conformance Overview` (IJT Facet Support block) and `IJT Facet Breakdown` sheet |
| `## 📝 Server Scope Notes` | `_render_review_sections()` | `Conformance Overview` (Server Scope Notes block) |
| `## 📋 Conformance Unit Details` | collapsed `<details>` in `render_conformance_summary()` | `Conformance Unit Details` sheet |
| `## 📌 Conformance Action Items` | `_render_review_sections()` | `Conformance Overview` (Conformance Action Items row) |
| `## 📐 IJT Facet Breakdown` | `_render_supports_block()` | `IJT Facet Breakdown` sheet |
| `<summary><b>Test Client Environment</b></summary>` | diagnostics `<details>` | `Conformance Overview` (Test Client Environment block) |
| `<summary><b>Skip &amp; Expected-Failure Diagnostics</b></summary>` | diagnostics `<details>` | `Skipped Test Cases` and `Expected Failures` sheets |

---

## 8. Out of scope for this glossary
- Tier definitions (`docs/TEST_TIERS.md`).
- Internal-only Python identifiers (`_ACTION_ITEM_LABEL_ORDER`, etc.) — these are implementation details and not user-facing.
- CI/CD plumbing terms not appearing in the rendered report.

---

## 9. Internal implementation terms

The source data still uses the internal discriminator **`rollup`** for grouped
facet definitions. The renderer and Excel workbook expose those rows as
**`Facet Group`**.

Internal Python (`kind == "rollup"` discriminator, `rollups` list variable) may
stay as-is because it is not user-visible.
