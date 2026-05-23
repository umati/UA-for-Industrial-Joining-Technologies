## IJT OPC UA — System Tests

> ✅ **All 7 / 7 jobs passed**
> **Branch:** `c2-phase-1b` &nbsp;·&nbsp; **Commit:** `abcdef12` &nbsp;·&nbsp; **Run:** [#84](https://github.example/ijt/actions/runs/84)

---

<a id="system-outcome-overview"></a>

### 📊 Test Outcome Overview

> ✅ **Status:** 0 failed jobs &nbsp;·&nbsp; 0 drift warnings &nbsp;·&nbsp; 0 skip-policy failures &nbsp;·&nbsp; 0 artifact warnings

| 🚦  | Outcome | Count |
| :-: | :------ | ----: |
| ✅  | Passed  | 2,432 |
| ❌  | Failed  |     0 |
| ⏭️  | Skipped |   154 |
| 🧮  | Total   | 2,586 |
| 🛠️  | Jobs    | 7 / 7 |

---

<a id="system-lane-results"></a>

### 🧪 Test Lane Results — 9 lanes

| 🚦 | Lane | Result | Test Results |
|:--:|:-----|:-------|:-------------|
| ✅ | OPC UA Server Docker smoke | success | 10 passed, 0 skipped |
| ✅ | Web Client Docker tests | success | Python: 680 passed, 0 skipped<br>JavaScript: 522 passed, 0 skipped |
| ✅ | Test Client conformance | success | 889 passed, 154 skipped |
| ✅ | Web Client live suites | success | 127 passed, 0 skipped |
| ✅ | Browser E2E suites | success | 66 passed, 0 skipped |
| ✅ | Console Client live | success | 18 passed, 0 skipped |
| ⏭️ | Console Client OPC UA security | skipped | Not reported |
| ✅ | C# Client live | success | 110 passed, 0 skipped |
| ⏭️ | C# Client OPC UA security | skipped | Not reported |

---

<a id="system-test-client-conformance-report"></a>

## IJT Conformance Test Report

🟢 **PASSED** · **0 action items** · **Validation 100.0% (98/98)** · **Server support 79.7% (98/123)**

### 📊 Conformance Overview

| Server Support Coverage | Validation Health | Conformance Action Items | Server Scope Notes |
|:---:|:---:|:---:|:---:|
| **79.7%** | **100.0%** | **🔴 0 Failed · 🟠 0 Blocked** | **⚪ 25 Not Supported · ℹ️ 3 With Notes** |

### 📋 Conformance Unit Details

<details>
<summary><b>28 rows needing review · 123 total CUs</b></summary>

Full CU detail lives in the Test Client artifact fixture.

</details>

---

<a id="system-component-test-results"></a>

### 🧬 Component Test Results — 5 components

| 🚦 | Component | Validation Scope | Container Test Results | Live/System Test Results | Notes |
|:--:|:----------|:-----------------|:-------------------|:---------------------|:------|
| ✅ | OPC UA Server | Linux container plus Windows live server processes | 10 passed, 0 skipped | Dedicated Windows ports 40461/40462/40464 feed client live suites | Docker smoke proves packaged Linux startup and namespace reachability |
| ✅ | Web Client | Docker unit/prod checks plus live Python/WebSocket and browser E2E | Python: 680 passed, 0 skipped<br>JavaScript: 522 passed, 0 skipped | Python/WebSocket live: 127 passed, 0 skipped<br>Browser E2E: 66 passed, 0 skipped | Headless Chromium baked into the IJT Browser CI image |
| ⏭️ | Test Client | Live conformance harness against OPC UA server | ➖ Not applicable | Smoke: 10 passed, 0 skipped<br>Conformance: 889 passed, 154 skipped | Not Implemented fixture marker |
| ✅ | Console Client | Live Python client behavior and OPC UA security coverage against OPC UA server | Not reported | 18 passed, 0 skipped | No additional notes |
| ✅ | C# Client | Nightly xUnit live behavior and OPC UA security coverage against OPC UA server | Not reported | 110 passed, 0 skipped | Nightly drift detection |

---

<a id="system-conformance-suites"></a>

### 📑 Conformance Suites — 2

| Suite | Port | Live Tests | Skipped | Notes |
|:------|-----:|----------:|--------:|:------|
| Test Client — Smoke sanity | 40462 | 10 ✅ | 0 | Server and namespace reachability |
| Test Client — Conformance | 40462 | 889 ✅ | 154 | Not Implemented fixture marker ([Skip Details](#system-skip-details)) |

---

<a id="system-skip-details"></a>

### ⏭️ Skip Details

_Each suite below is collapsed by default — click to inspect skip reasons._

<details><summary>⏭️ <b>Test Client — Conformance</b> — 154 skipped</summary>

| Reason | Count |
|:-------|------:|
| Skip details unavailable in JUnit XML | 153 |
| Not Implemented fixture marker | 1 |

</details>

---

<a id="system-performance-benchmarks"></a>

### ⏱️ Performance Benchmarks — 1 lane

| Lane | Samples | min (ms) | mean (ms) | p90 (ms) | max (ms) | Target | Result |
|:-----|--------:|---------:|----------:|---------:|---------:|:------:|:------:|
| Console Client — Result Transfer Time | 20 | 12.63 | 86.19 | 100.71 | 102.68 | mean &lt; 500 · p90 &lt; 500 | ✅ PASS |

_TOTAL = end-of-join → client callback. Full per-sample timing pipeline (joining, server acquisition/processing, wire) is recorded in JUnit XML test artifacts; download them for deep analysis._

---

<a id="system-performance-hotspots"></a>

### ⏱️ Performance Hotspots

<details><summary><b>Click to expand</b> — job, browser, C# and Test Client timing drilldown</summary>

> Source order: current workflow run jobs API first, then Web Client timing JSON, C# TRX artifacts, and Test Client JUnit durations when available. Missing timing data is omitted rather than estimated.

| Source | Item | Duration | Status |
|:-------|:-----|---------:|:-------|
| Browser timing artifact | 🏁 Browser Features (1/2) | 2.1 min | recorded 📊 |
| C# TRX class | C# Live — SlowTests | 1.2 min | recorded 📊 |
| C# TRX class | C# Live — FastTests | 5.5 s | recorded 📊 |

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

<a id="system-warnings-drift"></a>

### ⚠️ Warnings and Drift

<details><summary><b>Click to expand</b> — skip policy, drift, and artifact warnings</summary>

No skip policy failures, test-count drift warnings, or artifact warnings.

</details>


---

### 📎 Artifacts and Drilldown

<details><summary><b>Click to expand</b> — where to find raw JUnit, drill-down, and security results</summary>

> 📦 **Artifacts** — JUnit XML &nbsp;·&nbsp; 📋 **Checks** tab — per-test drill-down
> 🔒 Security audit (zizmor) results are in **CI** → Security → Code Scanning

</details>

---

<a id="system-per-client-quick-index"></a>

### 📚 Per-Client Quick Index — 5 clients

| Client / Component | Appears In |
|:-------------------|:-----------|
| OPC UA Server | [Test Lane Results](#system-lane-results); [Component Test Results](#system-component-test-results); [Performance Hotspots](#system-performance-hotspots) |
| Web Client | [Test Lane Results](#system-lane-results); [Component Test Results](#system-component-test-results); [Performance Hotspots](#system-performance-hotspots) |
| Test Client | [Test Lane Results](#system-lane-results); [Component Test Results](#system-component-test-results); [Conformance Suites](#system-conformance-suites); [Conformance Report](#system-test-client-conformance-report); [Performance Hotspots](#system-performance-hotspots) |
| Console Client | [Test Lane Results](#system-lane-results); [Component Test Results](#system-component-test-results); [Performance Benchmarks](#system-performance-benchmarks) |
| C# Client | [Test Lane Results](#system-lane-results); [Component Test Results](#system-component-test-results); [Performance Hotspots](#system-performance-hotspots) |
