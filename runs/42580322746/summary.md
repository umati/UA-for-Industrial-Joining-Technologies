## IJT OPC UA — System Tests

> ❌ **7 / 7 Jobs Failed &nbsp;·&nbsp; 0 Passed**
> **Branch:** `main` &nbsp;·&nbsp; **Commit:** `38324e47` &nbsp;·&nbsp; **Run:** [#1063](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/runs/42580322746)

> Full report below: [Outcome](#system-outcome-overview) · [Test Results](#system-test-results) · [CUs Needing Review](#system-cus-needing-review) · [Specification Test Report](#system-test-client-specification-test-report) · [Components](#system-component-test-results) · [Specification Test Suites](#system-specification-test-suites) · [Diagnostics](#system-skip-details) · [Performance](#system-performance-benchmarks) · [Artifacts](#system-artifacts-and-drilldown)

---

<a id="system-outcome-overview"></a>

### 📊 Test Outcome Overview

> ⚠️ **Status:** 7 Failed Jobs &nbsp;·&nbsp; 1 Baseline Warnings &nbsp;·&nbsp; 0 Skip-Policy Failures &nbsp;·&nbsp; 0 Artifact Warnings

| 🚦  | Outcome | Count |
| :-: | :------ | ----: |
| ✅  | Passed  |     0 |
| ❌  | Failed  |     0 |
| ⏭️  | Skipped |     0 |
| 🧮  | Total   |     0 |
| 🛠️  | Jobs    | 0 / 7 |

---

<a id="system-test-results"></a>

### 🧪 Test Results — 9 suites

| 🚦 | Suite | Result | Test Results |
|:--:|:------|:-------|:-------------|
| 🚫 | OPC UA Server Docker smoke | Cancelled | &bull; Not Reported |
| 🚫 | Web Client Docker tests | Cancelled | &bull; Python<br>&nbsp;&nbsp;&bull; Not Reported<br>&bull; JavaScript<br>&nbsp;&nbsp;&bull; Not Reported |
| 🚫 | Test Client specification tests | Cancelled | &bull; Not Reported |
| 🚫 | Web Client live suites | Cancelled | &bull; Not Reported |
| 🚫 | Browser E2E suites | Cancelled | &bull; Not Reported |
| 🚫 | Console Client live | Cancelled | &bull; Not Reported |
| ⏭️ | Console Client OPC UA security | Skipped | &bull; Not Reported |
| 🚫 | C# Client live | Cancelled | &bull; ✅&nbsp;Passed: 0<br>&bull; ⏭️&nbsp;Skipped: 0 |
| ⏭️ | C# Client OPC UA security | Skipped | &bull; Not Reported |

---

<a id="system-component-test-results"></a>

### 🧬 Component Test Results — 5 components

| 🚦 | Component | Validation Scope | Container Test Results | Live/System Test Results | Notes |
|:--:|:----------|:-----------------|:-------------------|:---------------------|:------|
| ✅ | OPC UA Server | Linux container plus Windows live server processes | &bull; Not Reported | Dedicated Windows ports 40461/40462/40464 feed client live suites | Docker smoke proves packaged Linux startup and namespace reachability |
| ✅ | Web Client | Docker unit/prod checks plus live Python/WebSocket and browser E2E | &bull; Python<br>&nbsp;&nbsp;&bull; Not Reported<br>&bull; JavaScript<br>&nbsp;&nbsp;&bull; Not Reported | &bull; Python/WebSocket Live<br>&nbsp;&nbsp;&bull; Not Reported<br>&bull; Browser E2E<br>&nbsp;&nbsp;&bull; Not Reported | Headless Chromium baked into the IJT Browser CI image |
| ✅ | Test Client | Live specification test harness against OPC UA server | ➖ Not Applicable | &bull; Smoke<br>&nbsp;&nbsp;&bull; Not Reported<br>&bull; Specification Tests<br>&nbsp;&nbsp;&bull; Not Reported | No additional notes |
| ✅ | Console Client | Live Python client behavior and OPC UA security coverage against OPC UA server | &bull; Not Reported | &bull; Not Reported | No additional notes |
| ✅ | C# Client | Nightly xUnit live behavior and OPC UA security coverage against OPC UA server | &bull; Not Reported | &bull; ✅&nbsp;Passed: 0<br>&bull; ⏭️&nbsp;Skipped: 0 | Nightly baseline check |

---

<a id="system-specification-test-suites"></a>

### 📑 Specification Test Suites — 2 suites

| Suite | Port | Live Tests | Skipped | Notes |
|:------|-----:|----------:|--------:|:------|
| Test Client — Smoke sanity | 40462 | — | — | Server and namespace reachability |
| Test Client — Specification Tests | 40462 | — | — | No additional notes ([Skip Details](#system-skip-details)) |

---

<a id="system-skip-details"></a>

### ⏭️ Skip Details

No skipped tests reported.

---

<a id="system-performance-hotspots"></a>

### ⏱️ Performance Hotspots

<details><summary><b>Click to expand</b> — job, browser, C# and Test Client timing drilldown</summary>

> Source order: current workflow run jobs API first, then Web Client timing JSON, C# TRX artifacts, and Test Client JUnit durations when available. Missing timing data is omitted rather than estimated.

| Source | Item | Duration | Status |
|:-------|:-----|---------:|:-------|
| Workflow job | 🏁 Browser CI image - resolve digest | 46.0 s | Passed ✅ |
| Workflow job | Web Client - Docker Tests | 38.0 s | Cancelled ⚪ |
| Workflow job | Performance Client - Windows Live Benchmark (port 40485) | 37.0 s | Cancelled ⚪ |
| Workflow job | C# Client - Live Tests (port 40464) | 36.0 s | Cancelled ⚪ |
| Workflow job | Console Client - Windows Live Tests (port 40461) | 36.0 s | Cancelled ⚪ |
| Workflow job | Test Client - Windows Live (port 40462) | 36.0 s | Cancelled ⚪ |
| Workflow job | OPC UA Server - Docker Smoke | 34.0 s | Cancelled ⚪ |
| Workflow job | Web Client - Direct OPC UA | 34.0 s | Cancelled ⚪ |
| Workflow job | Web Client - WebSocket API | 34.0 s | Cancelled ⚪ |
| Workflow job | Web Client - WebSocket Connection | 34.0 s | Cancelled ⚪ |

#### Bottleneck Spotlight

> 🏁 **Browser CI image - resolve digest** is the current longest reliable timing source (46.0 s, Workflow job).

<details><summary><b>Test Client Specification Test Timing Details</b></summary>

Per-test durations are not available in the current JUnit artifact.

</details>

</details>


---

<a id="system-warnings-baseline"></a>

### ⚠️ Warnings and Baseline Checks

<details><summary><b>Click to expand</b> — skip policy, baseline, and artifact warnings</summary>

#### Report Warnings

⚠️ **C# Client — Live**: 0 tests (-110 vs minimum 110) — tests may have disappeared. Investigate and re-anchor with `python tests/tools/update_integration_baseline.py --run 42580322746 --suite cs_live`.


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
| Image ref | `ghcr.io/umati/ua-for-industrial-joining-technologies/ijt-browser-ci@sha256:9655a589ff47c4f27a8079e1d27296acc2a01d7e6b55c635ac2050f6dfee363c` |
| Inputs fingerprint | `286ecbc7ee12a067aab6396ef2e31a50a214488f327a1dee7c2cc13cd24ae544` |

</details>

</details>

---

<a id="system-per-client-quick-index"></a>

### 📚 Per-Client Quick Index — 5 clients

| Client / Component | Appears In |
|:-------------------|:-----------|
| OPC UA Server | [Test Results](#system-test-results) · [Component Test Results](#system-component-test-results) · [Performance Hotspots](#system-performance-hotspots) |
| Web Client | [Test Results](#system-test-results) · [Component Test Results](#system-component-test-results) · [Performance Hotspots](#system-performance-hotspots) |
| Test Client | [Test Results](#system-test-results) · [Component Test Results](#system-component-test-results) · [Specification Test Suites](#system-specification-test-suites) · [Performance Hotspots](#system-performance-hotspots) |
| Console Client | [Test Results](#system-test-results) · [Component Test Results](#system-component-test-results) · [Performance Benchmarks](#system-performance-benchmarks) |
| C# Client | [Test Results](#system-test-results) · [Component Test Results](#system-component-test-results) · [Performance Hotspots](#system-performance-hotspots) |

---
Reports (no sign-in): [Runs](https://umati.github.io/UA-for-Industrial-Joining-Technologies/) · [CI](https://umati.github.io/UA-for-Industrial-Joining-Technologies/latest/ci/) · [System Tests](https://umati.github.io/UA-for-Industrial-Joining-Technologies/runs/42580322746/)
