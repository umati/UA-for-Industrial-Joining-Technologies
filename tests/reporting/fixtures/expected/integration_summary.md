## IJT OPC UA — System Tests

> ✅ **All 7 / 7 Jobs Passed**
> **Branch:** `c2-phase-1b` &nbsp;·&nbsp; **Commit:** `abcdef12` &nbsp;·&nbsp; **Run:** [#84](https://github.example/ijt/actions/runs/84)

---

<a id="system-outcome-overview"></a>

### 📊 Test Outcome Overview

> ✅ **Status:** 0 Failed Jobs &nbsp;·&nbsp; 0 Drift Warnings &nbsp;·&nbsp; 0 Skip-Policy Failures &nbsp;·&nbsp; 0 Artifact Warnings

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
| ✅ | OPC UA Server Docker smoke | Success | &bull; 10 Passed<br>&bull; 0 Skipped |
| ✅ | Web Client Docker tests | Success | &bull; Python<br>&nbsp;&nbsp;&bull; 680 Passed<br>&nbsp;&nbsp;&bull; 0 Skipped<br>&bull; JavaScript<br>&nbsp;&nbsp;&bull; 522 Passed<br>&nbsp;&nbsp;&bull; 0 Skipped |
| ✅ | Test Client conformance | Success | &bull; 889 Passed<br>&bull; 154 Skipped |
| ✅ | Web Client live suites | Success | &bull; 127 Passed<br>&bull; 0 Skipped |
| ✅ | Browser E2E suites | Success | &bull; 66 Passed<br>&bull; 0 Skipped |
| ✅ | Console Client live | Success | &bull; 18 Passed<br>&bull; 0 Skipped |
| ⏭️ | Console Client OPC UA security | Skipped | &bull; Not Reported |
| ✅ | C# Client live | Success | &bull; 110 Passed<br>&bull; 0 Skipped |
| ⏭️ | C# Client OPC UA security | Skipped | &bull; Not Reported |

---

<a id="system-test-client-conformance-report"></a>

## IJT Conformance Test Report

🟢 **Passed** · **0 action items** · **Validation 100.0% (98/98)** · **Server support 79.7% (98/123)**

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
| ✅ | OPC UA Server | Linux container plus Windows live server processes | &bull; 10 Passed<br>&bull; 0 Skipped | Dedicated Windows ports 40461/40462/40464 feed client live suites | Docker smoke proves packaged Linux startup and namespace reachability |
| ✅ | Web Client | Docker unit/prod checks plus live Python/WebSocket and browser E2E | &bull; Python<br>&nbsp;&nbsp;&bull; 680 Passed<br>&nbsp;&nbsp;&bull; 0 Skipped<br>&bull; JavaScript<br>&nbsp;&nbsp;&bull; 522 Passed<br>&nbsp;&nbsp;&bull; 0 Skipped | &bull; Python/WebSocket Live<br>&nbsp;&nbsp;&bull; 127 Passed<br>&nbsp;&nbsp;&bull; 0 Skipped<br>&bull; Browser E2E<br>&nbsp;&nbsp;&bull; 66 Passed<br>&nbsp;&nbsp;&bull; 0 Skipped | Headless Chromium baked into the IJT Browser CI image |
| ⏭️ | Test Client | Live conformance harness against OPC UA server | ➖ Not Applicable | &bull; Smoke<br>&nbsp;&nbsp;&bull; 10 Passed<br>&nbsp;&nbsp;&bull; 0 Skipped<br>&bull; Conformance<br>&nbsp;&nbsp;&bull; 889 Passed<br>&nbsp;&nbsp;&bull; 154 Skipped | Not Implemented fixture marker |
| ✅ | Console Client | Live Python client behavior and OPC UA security coverage against OPC UA server | &bull; Not Reported | &bull; 18 Passed<br>&bull; 0 Skipped | No additional notes |
| ✅ | C# Client | Nightly xUnit live behavior and OPC UA security coverage against OPC UA server | &bull; Not Reported | &bull; 110 Passed<br>&bull; 0 Skipped | Nightly drift detection |

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

<details><summary>⏭️ <b>Test Client — Conformance</b> — 154 Skipped</summary>

| Reason | Count |
|:-------|------:|
| Skip details unavailable in JUnit XML | 153 |
| Not Implemented fixture marker | 1 |

</details>

---

<a id="system-performance-benchmarks"></a>

### ⏱️ Performance Benchmarks — 1 lane

| Lane | Samples | min (ms) | mean (ms) | max (ms) | Target | Result |
|:-----|--------:|---------:|----------:|---------:|:------:|:------:|
| Console Client — Result Transfer Time | 20 | 12.63 | 86.19 | 102.68 | Mean &lt; 500 · Tail Check &lt; 500 | ✅ Pass |

_TOTAL = end of joining operation → client callback. The visible table keeps first-read latency numbers compact; the Pass/Fail gate also checks an internal tail-latency value. Full per-sample timing pipeline (joining, server acquisition/processing, wire) is recorded in JUnit XML test artifacts._

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
| OPC UA Server | [Test Lane Results](#system-lane-results); [Component Test Results](#system-component-test-results); [Performance Hotspots](#system-performance-hotspots) |
| Web Client | [Test Lane Results](#system-lane-results); [Component Test Results](#system-component-test-results); [Performance Hotspots](#system-performance-hotspots) |
| Test Client | [Test Lane Results](#system-lane-results); [Component Test Results](#system-component-test-results); [Conformance Suites](#system-conformance-suites); [Conformance Report](#system-test-client-conformance-report); [Performance Hotspots](#system-performance-hotspots) |
| Console Client | [Test Lane Results](#system-lane-results); [Component Test Results](#system-component-test-results); [Performance Benchmarks](#system-performance-benchmarks) |
| C# Client | [Test Lane Results](#system-lane-results); [Component Test Results](#system-component-test-results); [Performance Hotspots](#system-performance-hotspots) |
