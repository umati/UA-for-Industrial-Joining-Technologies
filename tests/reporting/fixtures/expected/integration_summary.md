## IJT OPC UA — System Tests

> ✅ **All 7 / 7 jobs passed &nbsp;·&nbsp; 2,586 tests &nbsp;·&nbsp; 0 failed &nbsp;·&nbsp; 154 skipped**
> **Branch:** `c2-phase-1b` &nbsp;·&nbsp; **Commit:** `abcdef12` &nbsp;·&nbsp; **Run:** [#84](https://github.example/ijt/actions/runs/84)
> Nightly and manual system tests — live OPC UA server behavior, browser E2E suites, Docker packaging, and conformance verification.

---

<a id="system-validation-overview"></a>

### Validation Overview

| Lane | Result | Test Results |
|:-----|:-------|:---------|
| OPC UA Server Docker smoke | ✅ success | ✅ 10, 0 skipped |
| Web Client Docker tests | ✅ success | Python: ✅ 680, 0 skipped<br>JavaScript: ✅ 522, 0 skipped |
| Test Client conformance | ✅ success | ✅ 1,043, 154 skipped |
| Web Client live suites | ✅ success | ✅ 127, 0 skipped |
| Browser E2E suites | ✅ success | ✅ 66, 0 skipped |
| Console Client live | ✅ success | ✅ 18, 0 skipped |
| Console Client OPC UA security | ⏭️ skipped | Not reported |
| C# Client live | ✅ success | ✅ 110, 0 skipped |
| C# Client OPC UA security | ⏭️ skipped | Not reported |

---

<a id="system-component-test-results"></a>

### Component Test Results

| Component | Validation Scope | Container Test Results | Live/System Test Results | Notes |
|:----------|:-----------------|:-------------------|:---------------------|:------|
| OPC UA Server | Linux container plus Windows live server processes | ✅ 10, 0 skipped | Dedicated Windows ports 40461/40462/40464 feed client live suites | Docker smoke proves packaged Linux startup and namespace reachability |
| Web Client | Docker unit/prod checks plus live Python/WebSocket and browser E2E | Python: ✅ 680, 0 skipped<br>JavaScript: ✅ 522, 0 skipped | Python/WebSocket live: ✅ 127, 0 skipped<br>Browser E2E: ✅ 66, 0 skipped | Headless Chromium baked into the IJT Browser CI image |
| Test Client | Live conformance harness against OPC UA server | Not applicable | Smoke: ✅ 10, 0 skipped<br>Conformance: ✅ 1,043, 154 skipped | Not Implemented fixture marker |
| Console Client | Live Python client behavior and OPC UA security coverage against OPC UA server | Not reported | ✅ 18, 0 skipped | No additional notes |
| C# Client | Nightly xUnit live behavior and OPC UA security coverage against OPC UA server | Not reported | ✅ 110, 0 skipped | Nightly drift detection |

---

<a id="system-conformance-overview"></a>

### Conformance Overview

| Suite | Port | Live Tests | Skipped | Notes |
|:------|-----:|----------:|--------:|:------|
| Test Client — Smoke sanity | 40462 | ✅ 10 | 0 | Server and namespace reachability |
| Test Client — Conformance | 40462 | ✅ 1,043 | 154 | Not Implemented fixture marker |

---

<a id="system-performance-hotspots"></a>

### Performance Hotspots

> Source order: current workflow run jobs API first, then Web Client timing JSON, C# TRX artifacts, and Test Client JUnit durations when available. Missing timing data is omitted rather than estimated.

| Source | Item | Duration | Status |
|:-------|:-----|---------:|:-------|
| Browser timing artifact | 🏁 Browser Features (1/2) | 2.1 min | 📊 recorded |
| C# TRX class | C# Live — SlowTests | 1.2 min | 📊 recorded |
| C# TRX class | C# Live — FastTests | 5.5 s | 📊 recorded |

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

---

<a id="system-warnings-drift"></a>

### Warnings and Drift

No skip policy failures, test-count drift warnings, or artifact warnings.

---

### Artifacts and Drilldown

> 📦 **Artifacts** — JUnit XML &nbsp;·&nbsp; 📋 **Checks** tab — per-test drill-down
> 🔒 Security audit (zizmor) results are in **CI** → Security → Code Scanning

#### Skip Details

<details><summary>⏭️ <b>Test Client — Conformance</b> — 154 skipped</summary>

| Reason | Count |
|:-------|------:|
| Skip details unavailable in JUnit XML | 153 |
| Not Implemented fixture marker | 1 |

</details>

---

<a id="system-per-client-quick-index"></a>

### Per-Client Quick Index

| Client / Component | Appears In |
|:-------------------|:-----------|
| OPC UA Server | [Validation Overview](#system-validation-overview); [Component Test Results](#system-component-test-results); [Performance Hotspots](#system-performance-hotspots) |
| Web Client | [Validation Overview](#system-validation-overview); [Component Test Results](#system-component-test-results); [Performance Hotspots](#system-performance-hotspots) |
| Test Client | [Validation Overview](#system-validation-overview); [Component Test Results](#system-component-test-results); [Conformance Overview](#system-conformance-overview); [Performance Hotspots](#system-performance-hotspots) |
| Console Client | [Validation Overview](#system-validation-overview); [Component Test Results](#system-component-test-results) |
| C# Client | [Validation Overview](#system-validation-overview); [Component Test Results](#system-component-test-results); [Performance Hotspots](#system-performance-hotspots) |
