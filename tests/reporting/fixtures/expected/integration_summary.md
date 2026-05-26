## IJT OPC UA — System Tests

> ✅ **All 7 / 7 Jobs Passed**
> **Branch:** `c2-phase-1b` &nbsp;·&nbsp; **Commit:** `abcdef12` &nbsp;·&nbsp; **Run:** [#84](https://github.example/ijt/actions/runs/84)

> Full report below: [Outcome](#system-outcome-overview) · [Test Results](#system-test-results) · [CUs Needing Review](#system-cus-needing-review) · [Conformance Report](#system-test-client-conformance-report) · [Components](#system-component-test-results) · [Conformance Suites](#system-conformance-suites) · [Diagnostics](#system-skip-details) · [Performance](#system-performance-benchmarks) · [Artifacts](#system-artifacts-and-drilldown)

---

<a id="system-outcome-overview"></a>

### 📊 Test Outcome Overview

> ✅ **Status:** 0 Failed Jobs &nbsp;·&nbsp; 0 Baseline Warnings &nbsp;·&nbsp; 0 Skip-Policy Failures &nbsp;·&nbsp; 0 Artifact Warnings

| 🚦  | Outcome | Count |
| :-: | :------ | ----: |
| ✅  | Passed  | 2,432 |
| ❌  | Failed  |     0 |
| ⏭️  | Skipped |   154 |
| 🧮  | Total   | 2,586 |
| 🛠️  | Jobs    | 7 / 7 |

---

<a id="system-test-results"></a>

### 🧪 Test Results — 9 suites

| 🚦 | Suite | Result | Test Results |
|:--:|:------|:-------|:-------------|
| ✅ | OPC UA Server Docker smoke | Success | &bull; ✅&nbsp;Passed: 10<br>&bull; ⏭️&nbsp;Skipped: 0 |
| ✅ | Web Client Docker tests | Success | &bull; Python<br>&nbsp;&nbsp;&bull; ✅&nbsp;Passed: 680<br>&nbsp;&nbsp;&bull; ⏭️&nbsp;Skipped: 0<br>&bull; JavaScript<br>&nbsp;&nbsp;&bull; ✅&nbsp;Passed: 522<br>&nbsp;&nbsp;&bull; ⏭️&nbsp;Skipped: 0 |
| ✅ | Test Client conformance | Success | &bull; ✅&nbsp;Passed: 889<br>&bull; ⏭️&nbsp;Skipped: 154 |
| ✅ | Web Client live suites | Success | &bull; ✅&nbsp;Passed: 127<br>&bull; ⏭️&nbsp;Skipped: 0 |
| ✅ | Browser E2E suites | Success | &bull; ✅&nbsp;Passed: 66<br>&bull; ⏭️&nbsp;Skipped: 0 |
| ✅ | Console Client live | Success | &bull; ✅&nbsp;Passed: 18<br>&bull; ⏭️&nbsp;Skipped: 0 |
| ⏭️ | Console Client OPC UA security | Skipped | &bull; Not Reported |
| ✅ | C# Client live | Success | &bull; ✅&nbsp;Passed: 110<br>&bull; ⏭️&nbsp;Skipped: 0 |
| ⏭️ | C# Client OPC UA security | Skipped | &bull; Not Reported |

---

<a id="system-test-client-conformance-report"></a>

## IJT Conformance Test Report

🟢 **Passed** · **0 action items** · **Validation 100.0% (98/98)** · **Server support 79.7% (98/123)**

### 📊 Conformance Overview

> 🚦 Review: 🔴 Failed · 🟠 Blocked · ⚪ Not Supported · ℹ️ With Notes

| Server Support Coverage | Validation Health | Conformance Action Items | Server Scope Notes |
|:---:|:---:|:---:|:---:|
| **79.7%** | **100.0%** | **🔴 0 Failed · 🟠 0 Blocked** | **⚪ 25 Not Supported · ℹ️ 3 With Notes** |
| 98 / 123 CUs server-supported | 98 / 98 server-supported CUs validated | No action needed | Information only. Review scope and caveats |

<a id="system-cus-needing-review"></a>

### 📋 CUs Needing Review — 28 rows

_Review rows only. Full 123-CU detail remains in `report.xlsx` and `report.html`._

Full review detail lives in the Test Client artifact fixture.

---
### 📎 Report References

- Term reference: see [REPORT_GLOSSARY.md](OPC_UA_Clients/Release2/IJT_Test_Client/docs/REPORT_GLOSSARY.md) for definitions of report terms.
- Full detail: download `report.xlsx` or `report.html` from the run artifacts.

---

<a id="system-component-test-results"></a>

### 🧬 Component Test Results — 5 components

| 🚦 | Component | Validation Scope | Container Test Results | Live/System Test Results | Notes |
|:--:|:----------|:-----------------|:-------------------|:---------------------|:------|
| ✅ | OPC UA Server | Linux container plus Windows live server processes | &bull; ✅&nbsp;Passed: 10<br>&bull; ⏭️&nbsp;Skipped: 0 | Dedicated Windows ports 40461/40462/40464 feed client live suites | Docker smoke proves packaged Linux startup and namespace reachability |
| ✅ | Web Client | Docker unit/prod checks plus live Python/WebSocket and browser E2E | &bull; Python<br>&nbsp;&nbsp;&bull; ✅&nbsp;Passed: 680<br>&nbsp;&nbsp;&bull; ⏭️&nbsp;Skipped: 0<br>&bull; JavaScript<br>&nbsp;&nbsp;&bull; ✅&nbsp;Passed: 522<br>&nbsp;&nbsp;&bull; ⏭️&nbsp;Skipped: 0 | &bull; Python/WebSocket Live<br>&nbsp;&nbsp;&bull; ✅&nbsp;Passed: 127<br>&nbsp;&nbsp;&bull; ⏭️&nbsp;Skipped: 0<br>&bull; Browser E2E<br>&nbsp;&nbsp;&bull; ✅&nbsp;Passed: 66<br>&nbsp;&nbsp;&bull; ⏭️&nbsp;Skipped: 0 | Headless Chromium baked into the IJT Browser CI image |
| ⏭️ | Test Client | Live conformance harness against OPC UA server | ➖ Not Applicable | &bull; Smoke<br>&nbsp;&nbsp;&bull; ✅&nbsp;Passed: 10<br>&nbsp;&nbsp;&bull; ⏭️&nbsp;Skipped: 0<br>&bull; Conformance<br>&nbsp;&nbsp;&bull; ✅&nbsp;Passed: 889<br>&nbsp;&nbsp;&bull; ⏭️&nbsp;Skipped: 154 | Capability and diagnostic notes grouped below |
| ✅ | Console Client | Live Python client behavior and OPC UA security coverage against OPC UA server | &bull; Not Reported | &bull; ✅&nbsp;Passed: 18<br>&bull; ⏭️&nbsp;Skipped: 0 | No additional notes |
| ✅ | C# Client | Nightly xUnit live behavior and OPC UA security coverage against OPC UA server | &bull; Not Reported | &bull; ✅&nbsp;Passed: 110<br>&bull; ⏭️&nbsp;Skipped: 0 | Nightly baseline check |

---

<a id="system-conformance-suites"></a>

### 📑 Conformance Suites — 2 suites

| Suite | Port | Live Tests | Skipped | Notes |
|:------|-----:|----------:|--------:|:------|
| Test Client — Smoke sanity | 40462 | 10 ✅ | 0 | Server and namespace reachability |
| Test Client — Conformance | 40462 | 889 ✅ | 154 ⏭️ | Capability and diagnostic notes grouped below ([Skip Details](#system-skip-details)) |

---

<a id="system-skip-details"></a>

### ⏭️ Skip Details

_Each suite below is collapsed by default — click to inspect skip reasons._

<details><summary><b>Other Diagnostics</b> — 154 skips</summary>

| Reason | Count |
|:-------|------:|
| Skip details unavailable in JUnit XML | 153 |
| Not Implemented fixture marker | 1 |

</details>

---

<a id="system-performance-benchmarks"></a>

### ⏱️ Performance Benchmarks — 1 benchmark

| Benchmark | Samples | min (ms) | average (ms) | max (ms) | Target | Result |
|:----------|--------:|---------:|-------------:|---------:|:-------|:------:|
| Console Client — Result Transfer Time | 20 | 12.63 | 86.19 | 102.68 | Average &lt; 500 ms · 90% of samples &lt; 500 ms | ✅ Pass |

_TOTAL = end of joining operation → client callback. The visible table shows min, average, and max latency. The Pass/Fail gate also requires at least 90% of samples to stay below the target. Per-sample timing pipeline details are recorded in JUnit XML test artifacts._

---

<a id="system-performance-hotspots"></a>

### ⏱️ Performance Hotspots

<details><summary><b>Click to expand</b> — job, browser, C# and Test Client timing drilldown</summary>

> Source order: current workflow run jobs API first, then Web Client timing JSON, C# TRX artifacts, and Test Client JUnit durations when available. Missing timing data is omitted rather than estimated.

| Source | Item | Duration | Status |
|:-------|:-----|---------:|:-------|
| Browser timing artifact | 🏁 Browser Features (1/2) | 2.1 min | Recorded 📊 |
| C# TRX class | C# Live — SlowTests | 1.2 min | Recorded 📊 |
| C# TRX class | C# Live — FastTests | 5.5 s | Recorded 📊 |

#### Bottleneck Spotlight

> 🏁 **Browser Features (1/2)** is the current longest reliable timing source (2.1 min, Browser timing artifact).

<details><summary><b>Browser Feature Stage Timing</b></summary>

| Shard | Total | pip-install | npm-install | Playwright install | Playwright features | Other |
|:------|------:|------------:|------------:|-------------------:|--------------------:|------:|
| 1/2 | 2.1 min | 10.0 s | 20.0 s | 30.0 s | 1.0 min | 3.4 s |

</details>

<details><summary><b>C# Live Timing Details</b></summary>

| Class | Tests | Total | Avg | Max |
|:------|------:|------:|----:|----:|
| SlowTests | 1 | 1.2 min | 1.2 min | 1.2 min |
| FastTests | 1 | 5.5 s | 5.5 s | 5.5 s |

#### Slowest C# Live Tests

| Test | Duration | Outcome |
|:-----|---------:|:--------|
| RunsJoiningCycle | 1.2 min | Passed |
| ReadsServerStatus | 5.5 s | Passed |

</details>

<details><summary><b>Test Client Conformance Timing Details</b></summary>

Per-test durations are not available in the current JUnit artifact.

</details>

</details>


---

<a id="system-warnings-baseline"></a>

### ⚠️ Warnings and Baseline Checks

<details><summary><b>Click to expand</b> — skip policy, baseline, and artifact warnings</summary>

No skip policy failures, baseline warnings, or artifact warnings.

</details>


---

<a id="system-artifacts-and-drilldown"></a>

### 📎 Artifacts and Drilldown

<details><summary><b>Click to expand</b> — where to find raw JUnit, drill-down, and security results</summary>

> 📦 **Artifacts** — JUnit XML &nbsp;·&nbsp; 📋 **Checks** tab — per-test drill-down
> 🔒 Security audit (zizmor) results are in **CI** → Security → Code Scanning

<details><summary><b>Browser CI Image</b></summary>

| Field | Value |
|:------|:------|
| Plan | `cached` |
| Image ref | `ghcr.io/umati/ua-for-industrial-joining-technologies/ijt-browser-ci@sha256:4910c3014c87914a9b041edcd05ea018ab13db65461707602d18c5f33e0ece87` |
| Inputs fingerprint | `e569f8a7754eb9a1979bd341e274167c43d2b1985e96238270cc7140ec89aa31` |

</details>

</details>

---

<a id="system-per-client-quick-index"></a>

### 📚 Per-Client Quick Index — 5 clients

| Client / Component | Appears In |
|:-------------------|:-----------|
| OPC UA Server | [Test Results](#system-test-results) · [Component Test Results](#system-component-test-results) · [Performance Hotspots](#system-performance-hotspots) |
| Web Client | [Test Results](#system-test-results) · [Component Test Results](#system-component-test-results) · [Performance Hotspots](#system-performance-hotspots) |
| Test Client | [Test Results](#system-test-results) · [Component Test Results](#system-component-test-results) · [Conformance Suites](#system-conformance-suites) · [Conformance Report](#system-test-client-conformance-report) · [Performance Hotspots](#system-performance-hotspots) |
| Console Client | [Test Results](#system-test-results) · [Component Test Results](#system-component-test-results) · [Performance Benchmarks](#system-performance-benchmarks) |
| C# Client | [Test Results](#system-test-results) · [Component Test Results](#system-component-test-results) · [Performance Hotspots](#system-performance-hotspots) |
