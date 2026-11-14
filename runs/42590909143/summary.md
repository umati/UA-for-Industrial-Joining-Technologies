## IJT OPC UA — System Tests

> ✅ **All 9 / 9 Jobs Passed**
> **Branch:** `main` &nbsp;·&nbsp; **Commit:** `6cab5fd4` &nbsp;·&nbsp; **Run:** [#1071](https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/runs/42590909143)

> Full report below: [Outcome](#system-outcome-overview) · [Test Results](#system-test-results) · [CUs Needing Review](#system-cus-needing-review) · [Specification Test Report](#system-test-client-specification-test-report) · [Components](#system-component-test-results) · [Specification Test Suites](#system-specification-test-suites) · [Diagnostics](#system-skip-details) · [Performance](#system-performance-benchmarks) · [Artifacts](#system-artifacts-and-drilldown)

---

<a id="system-outcome-overview"></a>

### 📊 Test Outcome Overview

> ✅ **Status:** 0 Failed Jobs &nbsp;·&nbsp; 0 Baseline Warnings &nbsp;·&nbsp; 0 Skip-Policy Failures &nbsp;·&nbsp; 0 Artifact Warnings

| 🚦  | Outcome | Count |
| :-: | :------ | ----: |
| ✅  | Passed  | 3,014 |
| ❌  | Failed  |     0 |
| ⏭️  | Skipped |   152 |
| 🧮  | Total   | 3,166 |
| 🛠️  | Jobs    | 9 / 9 |

---

<a id="system-test-results"></a>

### 🧪 Test Results — 9 suites

| 🚦 | Suite | Result | Test Results |
|:--:|:------|:-------|:-------------|
| ✅ | OPC UA Server Docker smoke | Success | &bull; ✅&nbsp;Passed: 10<br>&bull; ⏭️&nbsp;Skipped: 0 |
| ✅ | Web Client Docker tests | Success | &bull; Python<br>&nbsp;&nbsp;&bull; ✅&nbsp;Passed: 889<br>&nbsp;&nbsp;&bull; ⏭️&nbsp;Skipped: 0<br>&bull; JavaScript<br>&nbsp;&nbsp;&bull; ✅&nbsp;Passed: 701<br>&nbsp;&nbsp;&bull; ⏭️&nbsp;Skipped: 0 |
| ✅ | Test Client specification tests | Success | &bull; ✅&nbsp;Passed: 920<br>&bull; ⏭️&nbsp;Skipped: 152 |
| ✅ | Web Client live suites | Success | &bull; ✅&nbsp;Passed: 128<br>&bull; ⏭️&nbsp;Skipped: 0 |
| ✅ | Browser E2E suites | Success | &bull; ✅&nbsp;Passed: 68<br>&bull; ⏭️&nbsp;Skipped: 0 |
| ✅ | Console Client live | Success | &bull; ✅&nbsp;Passed: 18<br>&bull; ⏭️&nbsp;Skipped: 0 |
| ✅ | Console Client OPC UA security | Success | &bull; ✅&nbsp;Passed: 78<br>&bull; ⏭️&nbsp;Skipped: 0 |
| ✅ | C# Client live | Success | &bull; ✅&nbsp;Passed: 110<br>&bull; ⏭️&nbsp;Skipped: 0 |
| ✅ | C# Client OPC UA security | Success | &bull; ✅&nbsp;Passed: 82<br>&bull; ⏭️&nbsp;Skipped: 0 |

---

<a id="system-test-client-specification-test-report"></a>

## IJT Specification Test Report

🟢 **Passed** · **0 action items** · **Validation 100.0% (98/98)** · **Server support 79.7% (98/123)**

| Item | Value |
|---|---|
| **Server** | OPC UA IJT Server Simulator (`opc.tcp://localhost:40462`) |
| **Capability profile** | Full IJT Base Specification Coverage |
| **Run** | 2026-11-09 09:12 UTC · Duration 4m 6s |
| **Build** | commit `6cab5fd` · run logs: https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/runs/42590909143 |

### 📊 Specification Test Overview

> 🚦 Review: 🔴 Failed · 🟠 Blocked · ⚪ Not Supported · ℹ️ With Notes

| Server Support Coverage | Validation Health | Specification Test Action Items | Server Scope Notes |
|:---:|:---:|:---:|:---:|
| **79.7%** | **100.0%** | **🔴 0 Failed · 🟠 0 Blocked** | **⚪ 25 Not Supported · ℹ️ 1 With Notes** |
| 98 / 123 CUs server-supported | 98 / 98 server-supported CUs validated | No action needed | Information only. Review scope and caveats |

**Live tests (unique):** 1072 — 920 passed · 0 failed · 0 errors · 152 skipped · **CU-marked:** 855 (217 without CU marker) · **CUs (123):** 98 exercised · 25 skipped only · 0 not run · 0 without tests

<details>
<summary><b>Per-CU test counts</b> — 123 CUs, 855 CU-marked tests, 887 CU test links</summary>

_A test linked to several CUs is counted in each CU row, so rows overlap and must not be summed. Exercised = at least one test passed, failed or errored; skips never count as exercised. Failed = test assertion failure; Error = setup/teardown failure._

| CU | Status | Tests | Passed | Failed | Error | Not Supported | Blocked | Accepted Policy | Environment | Skipped | Untested |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| IJT Abort Joining Process | Exercised | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Acknowledge Results | Skipped only | 7 | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 0 |
| IJT Asset Connection Event | Exercised | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Asset Connection State Event | Exercised | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Asset Enable State Event | Exercised | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Asset Management | Exercised | 38 | 38 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Asset Management Accessory | Exercised | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Asset Management Additional Information | Exercised | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Asset Management Battery | Exercised | 12 | 12 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Asset Management Battery Operation Cycle Counter | Exercised | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Asset Management Cable | Exercised | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Asset Management Calibration | Exercised | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Asset Management Controller | Exercised | 15 | 15 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Asset Management Feeder | Exercised | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Asset Management Health | Exercised | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Asset Management Machinery Building Blocks | Exercised | 10 | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Asset Management Memory Device | Exercised | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Asset Management Monitoring Health | Exercised | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Asset Management Operation Counters | Exercised | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Asset Management Power Supply | Exercised | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Asset Management Sensor | Exercised | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Asset Management Service | Exercised | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Asset Management Servo | Exercised | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Asset Management Software | Exercised | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Asset Management Sub Component | Exercised | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Asset Management Tool | Exercised | 15 | 15 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Asset Management Tool Operation Cycle Counter | Exercised | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Asset Management Virtual Station | Exercised | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Basic Result | Exercised | 20 | 20 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Batch Result | Exercised | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Batch Result Counters | Exercised | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Consolidated Result With References | Exercised | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Decrement Joining Process Counter | Exercised | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Delete Joining Process | Skipped only | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 |
| IJT Delete Joint | Exercised | 7 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Delete Joint Component | Skipped only | 3 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 |
| IJT Delete Joint Design | Skipped only | 3 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 |
| IJT Deselect Joining Process | Exercised | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Disconnect Asset | Skipped only | 4 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 |
| IJT Enable Tool | Exercised | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Engineering Units | Exercised | 10 | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Event Condition Classes | Exercised | 30 | 30 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Event Payload | Exercised | 39 | 39 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Event Payload Associated Entities | Exercised | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Event Payload Reported Values | Exercised | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Execute Operation | Skipped only | 4 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 |
| IJT Feedback Methods | Skipped only | 6 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 |
| IJT Get Error Information | Skipped only | 4 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 |
| IJT Get Identifiers | Exercised | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Get Joining Process | Skipped only | 5 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 |
| IJT Get Joining Process List | Exercised | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Get Joining Process Revision List | Skipped only | 4 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 |
| IJT Get Joint | Exercised | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Get Joint Component | Skipped only | 5 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 |
| IJT Get Joint Component List | Skipped only | 4 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 |
| IJT Get Joint Design | Skipped only | 5 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 |
| IJT Get Joint Design List | Skipped only | 4 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 |
| IJT Get Joint List | Exercised | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Get Joint Revision List | Skipped only | 5 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 |
| IJT Get Latest Result | Exercised | 13 | 13 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Get Result By ID | Exercised | 11 | 11 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Get Result With Filter Criteria | Exercised | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Get Selected Joining Program | Exercised | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Identifiers Event | Exercised | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Increment Joining Process Counter | Exercised | 6 | 5 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| IJT Intervention Result | Exercised | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT IO Signals Methods | Exercised | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Job Result | Exercised | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Joining Process Management | Exercised | 37 | 27 | 0 | 0 | 0 | 0 | 10 | 0 | 0 | 0 |
| IJT Joining Result Errors | Exercised | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Joining Result Failure Reason | Exercised | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Joining Result Overall Result Values | Exercised | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Joining Result Step Results | Exercised | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Joining Result Trace | Exercised | 11 | 11 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Joining System Base | Exercised | 13 | 13 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Joining System Identification | Exercised | 14 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Joining System Machinery Building Blocks | Exercised | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Joint Component Data | Skipped only | 4 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 |
| IJT Joint Data | Exercised | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Joint Design Data | Skipped only | 4 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 |
| IJT Joint Management | Exercised | 25 | 16 | 0 | 0 | 0 | 0 | 9 | 0 | 0 | 0 |
| IJT Method Input Argument | Exercised | 13 | 8 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 |
| IJT Partial Consolidated Result | Exercised | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Reboot Asset | Skipped only | 4 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 |
| IJT Request Results | Exercised | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Request Unacknowledged Results | Skipped only | 7 | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 0 |
| IJT Requested Result Event Access | Exercised | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Requested Result Variable Access | Exercised | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Reset Identifiers | Exercised | 10 | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Reset Joining Process | Exercised | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Result Additional Data | Exercised | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Result Content | Exercised | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Result Event Access | Exercised | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Result Extended Meta Data | Exercised | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Result External Identifiers | Exercised | 7 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Result Internal Identifiers | Exercised | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Result Management | Exercised | 13 | 13 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Result Processing Times | Exercised | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Result Processing Times Durations | Exercised | 10 | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Result Value Final Tag | Exercised | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Result Value Trace Point Index | Exercised | 7 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Result Value Trace Point Time Offset | Exercised | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Result Variable Access | Exercised | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Select Joining Process | Exercised | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Select Joint | Exercised | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Select Process Event | Exercised | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Self Contained Consolidated Result | Exercised | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Send Identifiers | Exercised | 14 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Send Joining Process | Skipped only | 5 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 |
| IJT Send Joint | Exercised | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Send Joint Component | Skipped only | 6 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 |
| IJT Send Joint Design | Skipped only | 6 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 |
| IJT Set Calibration | Skipped only | 4 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 |
| IJT Set Joining Process Counter | Exercised | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Set Joining Process Mapping | Skipped only | 3 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 |
| IJT Set Joining Process Size | Exercised | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Set Offline Timer | Skipped only | 4 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 |
| IJT Set Time | Exercised | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Single Result | Exercised | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Start Joining Process | Exercised | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Start Selected Joining | Exercised | 7 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Sync Result | Exercised | 7 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Sync Result Counters | Exercised | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**Skipped-only CUs (25)**

| CU | Tests | Main reasons |
|---|---:|---|
| IJT Acknowledge Results | 7 | Not Supported (7): Method 'AcknowledgeResults' is not supported NOT SUPPORTED |
| IJT Delete Joining Process | 2 | Not Supported (2): Method 'DeleteJoiningProcess' is not supported NOT SUPPORTED |
| IJT Delete Joint Component | 3 | Not Supported (3): Method 'DeleteJointComponent' is not supported NOT SUPPORTED |
| IJT Delete Joint Design | 3 | Not Supported (3): Method 'DeleteJointDesign' is not supported NOT SUPPORTED |
| IJT Disconnect Asset | 4 | Not Supported (4): Method 'DisconnectAsset' is not supported NOT SUPPORTED |
| IJT Execute Operation | 4 | Not Supported (4): Method 'ExecuteOperation' is not supported NOT SUPPORTED |
| IJT Feedback Methods | 6 | Not Supported (6): Methods 'GetFeedbackFileList', 'SendFeedback' are not supported NOT SUPPORTED |
| IJT Get Error Information | 4 | Not Supported (4): Method 'GetErrorInformation' is not supported NOT SUPPORTED |
| IJT Get Joining Process | 5 | Not Supported (5): Method 'GetJoiningProcess' is not supported NOT SUPPORTED |
| IJT Get Joining Process Revision List | 4 | Not Supported (4): Method 'GetJoiningProcessRevisionList' is not supported NOT SUPPORTED |
| IJT Get Joint Component | 5 | Not Supported (5): Method 'GetJointComponent' is not supported NOT SUPPORTED |
| IJT Get Joint Component List | 4 | Not Supported (4): Method 'GetJointComponentList' is not supported NOT SUPPORTED |
| IJT Get Joint Design | 5 | Not Supported (5): Method 'GetJointDesign' is not supported NOT SUPPORTED |
| IJT Get Joint Design List | 4 | Not Supported (4): Method 'GetJointDesignList' is not supported NOT SUPPORTED |
| IJT Get Joint Revision List | 5 | Not Supported (5): Method 'GetJointRevisionList' is not supported NOT SUPPORTED |
| IJT Joint Component Data | 4 | Not Supported (4): Conformance unit 'IJT Joint Component Data' is not supported NOT SUPPORTED |
| IJT Joint Design Data | 4 | Not Supported (4): Conformance unit 'IJT Joint Design Data' is not supported NOT SUPPORTED |
| IJT Reboot Asset | 4 | Not Supported (4): Method 'RebootAsset' is not supported NOT SUPPORTED |
| IJT Request Unacknowledged Results | 7 | Not Supported (7): Method 'RequestUnacknowledgedResults' is not supported NOT SUPPORTED |
| IJT Send Joining Process | 5 | Not Supported (5): Method 'SendJoiningProcess' is not supported NOT SUPPORTED |
| IJT Send Joint Component | 6 | Not Supported (6): Method 'SendJointComponent' is not supported NOT SUPPORTED |
| IJT Send Joint Design | 6 | Not Supported (6): Method 'SendJointDesign' is not supported NOT SUPPORTED |
| IJT Set Calibration | 4 | Not Supported (4): Method 'SetCalibration' is not supported NOT SUPPORTED |
| IJT Set Joining Process Mapping | 3 | Not Supported (3): Method 'SetJoiningProcessMapping' is not supported NOT SUPPORTED |
| IJT Set Offline Timer | 4 | Not Supported (4): Method 'SetOfflineTimer' is not supported NOT SUPPORTED |

</details>

<a id="system-cus-needing-review"></a>

### 📋 CUs Needing Review — 26 rows

_Review rows only. Full 123-CU detail remains in `report.xlsx` and `report.html`._

| Status | CU | Server Supported | Reason | Tests | Passed | Not Supported | Blocked | Failures |
|---|---|---|---|---:|---:|---:|---:|---:|
| ⚪&nbsp;Not&nbsp;Supported | IJT Acknowledge Results | No | Method 'AcknowledgeResults' is not supported | 7 | 0 | 7 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Delete Joining Process | No | Method 'DeleteJoiningProcess' is not supported | 2 | 0 | 2 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Delete Joint Component | No | Method 'DeleteJointComponent' is not supported | 3 | 0 | 3 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Delete Joint Design | No | Method 'DeleteJointDesign' is not supported | 3 | 0 | 3 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Disconnect Asset | No | Method 'DisconnectAsset' is not supported | 4 | 0 | 4 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Execute Operation | No | Method 'ExecuteOperation' is not supported | 4 | 0 | 4 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Feedback Methods | No | Methods 'GetFeedbackFileList', 'SendFeedback' are not supported | 6 | 0 | 6 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Get Error Information | No | Method 'GetErrorInformation' is not supported | 4 | 0 | 4 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Get Joining Process | No | Method 'GetJoiningProcess' is not supported | 5 | 0 | 5 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Get Joining Process Revision List | No | Method 'GetJoiningProcessRevisionList' is not supported | 4 | 0 | 4 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Get Joint Component | No | Method 'GetJointComponent' is not supported | 5 | 0 | 5 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Get Joint Component List | No | Method 'GetJointComponentList' is not supported | 4 | 0 | 4 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Get Joint Design | No | Method 'GetJointDesign' is not supported | 5 | 0 | 5 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Get Joint Design List | No | Method 'GetJointDesignList' is not supported | 4 | 0 | 4 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Get Joint Revision List | No | Method 'GetJointRevisionList' is not supported | 5 | 0 | 5 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Joint Component Data | No | Conformance unit 'IJT Joint Component Data' is not supported | 4 | 0 | 4 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Joint Design Data | No | Conformance unit 'IJT Joint Design Data' is not supported | 4 | 0 | 4 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Reboot Asset | No | Method 'RebootAsset' is not supported | 4 | 0 | 4 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Request Unacknowledged Results | No | Method 'RequestUnacknowledgedResults' is not supported | 7 | 0 | 7 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Send Joining Process | No | Method 'SendJoiningProcess' is not supported | 5 | 0 | 5 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Send Joint Component | No | Method 'SendJointComponent' is not supported | 6 | 0 | 6 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Send Joint Design | No | Method 'SendJointDesign' is not supported | 6 | 0 | 6 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Set Calibration | No | Method 'SetCalibration' is not supported | 4 | 0 | 4 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Set Joining Process Mapping | No | Method 'SetJoiningProcessMapping' is not supported | 3 | 0 | 3 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Set Offline Timer | No | Method 'SetOfflineTimer' is not supported | 4 | 0 | 4 | 0 | 0 |
| ℹ️&nbsp;With&nbsp;Notes | IJT Increment Joining Process Counter | Yes | Blocked: No target-server counter workflow is configured | 6 | 5 | 0 | 1 | 0 |

### 🧩 IJT Facet Support — 11 Supported · 6 Partial · 2 Not Supported

> 🚦 Support: ✅ Supported · ⚠️ Partially Supported · ⚪ Not Supported

_Auto-generated from the server profile and specification test outcomes. Full detail is in IJT Facet Breakdown._

- ⚪ **Joint Component** — Not Supported. Joint component send, list, read, data, and delete coverage.
- ⚪ **Joint Design** — Not Supported. Joint design send, list, read, data, and delete coverage.
- ⚠️ **Additional Asset Methods** — Partially Supported. Optional asset operation methods beyond the asset topology baseline.
- ⚠️ **Additional Process Methods** — Partially Supported. Optional joining process definition, mapping, counter, delete, and revision-list methods.
- ⚠️ **Asset Connection** — Partially Supported. Asset connection facet for DisconnectAsset and asset connection event coverage.
- ⚠️ **Joint** — Partially Supported. Joint management base object and methods for sending, listing, selecting, reading, deleting, and revising joints.
- ⚠️ **Sequential Process Operations** — Partially Supported. Sequential joining process execution and process counter/size operations.
- ⚠️ **Stored Result** — Partially Supported. Stored/requested result workflows including result requests, requested-result access, acknowledgements, and unacknowledged-result requests.
- ✅ **Asset Management Assets** — Supported. Asset topology, asset identification, Machinery building blocks, health, service, calibration, and individual IJT asset type coverage.
- ✅ **Basic Joining System** — Supported. Minimum conformance requirement for any OPC UA IJT server: JoiningSystem structure, identification, and Machinery building blocks.
- ✅ **Batch Result** — Supported. Batch and intervention result support with related result counters.
- ✅ **Enable Tool** — Supported. EnableAsset/enable-tool workflow support and corresponding asset enable state event coverage.

_Showing the most relevant capability areas here. Full capability detail is in IJT Facet Breakdown. Capability area counts: 11 Supported · 6 Partially Supported · 2 Not Supported._

### 📐 IJT Facet Breakdown

<details>
<summary><b>21 facet rows</b></summary>

| Facet | Type | CUs | Server Supported CUs | Server Support % | Supported CUs Validated % | Outcome Counts | Outcome Rollup |
|---|---|---:|---:|---:|---:|---|---|
| IJT Result Server Facet | Facet | 12 | 12 | 100.0% | 100.0% | 🟢&nbsp;Supported: 12 | 🟢&nbsp;Supported |
| IJT Joining Result Server Facet | Facet | 7 | 7 | 100.0% | 100.0% | 🟢&nbsp;Supported: 7 | 🟢&nbsp;Supported |
| IJT Sync Result Server Facet | Facet | 2 | 2 | 100.0% | 100.0% | 🟢&nbsp;Supported: 2 | 🟢&nbsp;Supported |
| IJT Batch Result Server Facet | Facet | 3 | 3 | 100.0% | 100.0% | 🟢&nbsp;Supported: 3 | 🟢&nbsp;Supported |
| IJT Stored Result Server Facet | Facet | 5 | 3 | 60.0% | 100.0% | 🟢&nbsp;Supported: 3<br>⚪&nbsp;Not&nbsp;Supported: 2 | 🟩&nbsp;Supported&nbsp;with&nbsp;Notes |
| IJT Asset Management Assets Server Facet | Facet | 23 | 23 | 100.0% | 100.0% | 🟢&nbsp;Supported: 23 | 🟢&nbsp;Supported |
| IJT Identifiers Methods Server Facet | Facet | 3 | 3 | 100.0% | 100.0% | 🟢&nbsp;Supported: 3 | 🟢&nbsp;Supported |
| IJT Additional Asset Methods Server Facet | Facet | 9 | 2 | 22.2% | 100.0% | 🟢&nbsp;Supported: 2<br>⚪&nbsp;Not&nbsp;Supported: 7 | 🟩&nbsp;Supported&nbsp;with&nbsp;Notes |
| IJT Event Management Server Facet | Facet | 8 | 8 | 100.0% | 100.0% | 🟢&nbsp;Supported: 8 | 🟢&nbsp;Supported |
| IJT Enable Tool Server Facet | Facet | 2 | 2 | 100.0% | 100.0% | 🟢&nbsp;Supported: 2 | 🟢&nbsp;Supported |
| IJT Asset Connection Server Facet | Facet | 3 | 2 | 66.7% | 100.0% | 🟢&nbsp;Supported: 2<br>⚪&nbsp;Not&nbsp;Supported: 1 | 🟩&nbsp;Supported&nbsp;with&nbsp;Notes |
| IJT Joining Process Base Server Facet | Facet | 2 | 2 | 100.0% | 100.0% | 🟢&nbsp;Supported: 2 | 🟢&nbsp;Supported |
| IJT General Process Operations Server Facet | Facet | 6 | 6 | 100.0% | 100.0% | 🟢&nbsp;Supported: 6 | 🟢&nbsp;Supported |
| IJT Sequential Process Operations Server Facet | Facet | 4 | 4 | 100.0% | 100.0% | 🟢&nbsp;Supported: 3<br>ℹ️&nbsp;With&nbsp;Notes: 1 | 🟩&nbsp;Supported&nbsp;with&nbsp;Notes |
| IJT Additional Process Methods Server Facet | Facet | 6 | 1 | 16.7% | 100.0% | 🟢&nbsp;Supported: 1<br>⚪&nbsp;Not&nbsp;Supported: 5 | 🟩&nbsp;Supported&nbsp;with&nbsp;Notes |
| IJT Joint Server Facet | Facet | 8 | 7 | 87.5% | 100.0% | 🟢&nbsp;Supported: 7<br>⚪&nbsp;Not&nbsp;Supported: 1 | 🟩&nbsp;Supported&nbsp;with&nbsp;Notes |
| IJT Joint Design Server Facet | Facet | 5 | 0 | 0.0% | Not Applicable | ⚪&nbsp;Not&nbsp;Supported: 5 | ⚪&nbsp;Not&nbsp;Supported |
| IJT Joint Component Server Facet | Facet | 5 | 0 | 0.0% | Not Applicable | ⚪&nbsp;Not&nbsp;Supported: 5 | ⚪&nbsp;Not&nbsp;Supported |
| Basic Joining System Server Facet | Facet | 3 | 3 | 100.0% | 100.0% | 🟢&nbsp;Supported: 3 | 🟢&nbsp;Supported |
| General Joining System Server Facet | Facet Group | 39 | 39 | 100.0% | 100.0% | 🟢&nbsp;Supported: 39 | 🟢&nbsp;Supported |
| Joining System Selectable Features Server Facet | Facet Group | 84 | 59 | 70.2% | 100.0% | 🟢&nbsp;Supported: 58<br>ℹ️&nbsp;With&nbsp;Notes: 1<br>⚪&nbsp;Not&nbsp;Supported: 25 | 🟩&nbsp;Supported&nbsp;with&nbsp;Notes |

</details>

<details>
<summary><b>Test Client Environment</b></summary>

| Item | Value |
|---|---|
| Test Client commit | `6cab5fd` |
| Python | 3.14.10 |
| asyncua | 2.1.0 |
| Host OS | Windows-2025Server-10.0.26100-SP0 |
| Repro command | `python run_all_tests.py` |
| Run logs | https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/runs/42590909143 |

</details>

<details>
<summary><b>Skip &amp; Expected-Failure Diagnostics</b></summary>

_Diagnostic skip buckets and expected failures. The "Not Supported:" reasons are intentionally filtered here — server-unsupported CUs are tracked separately in "CUs Needing Review"._

##### Diagnostic Skips

_No diagnostic skips on this run._

</details>

---
### 📎 Report References

- Term reference: see [REPORT_GLOSSARY.md](https://github.com/umati/UA-for-Industrial-Joining-Technologies/blob/6cab5fd4823d635632d4aaff27da5c5d7dacdad4/OPC_UA_Clients/Release2/IJT_Test_Client/docs/REPORT_GLOSSARY.md) for definitions of report terms.
- Full detail: download `report.xlsx` or `report.html` from the run artifacts.

---

<a id="system-component-test-results"></a>

### 🧬 Component Test Results — 5 components

| 🚦 | Component | Validation Scope | Container Test Results | Live/System Test Results | Notes |
|:--:|:----------|:-----------------|:-------------------|:---------------------|:------|
| ✅ | OPC UA Server | Linux container plus Windows live server processes | &bull; ✅&nbsp;Passed: 10<br>&bull; ⏭️&nbsp;Skipped: 0 | Dedicated Windows ports 40461/40462/40464 feed client live suites | Docker smoke proves packaged Linux startup and namespace reachability |
| ✅ | Web Client | Docker unit/prod checks plus live Python/WebSocket and browser E2E | &bull; Python<br>&nbsp;&nbsp;&bull; ✅&nbsp;Passed: 889<br>&nbsp;&nbsp;&bull; ⏭️&nbsp;Skipped: 0<br>&bull; JavaScript<br>&nbsp;&nbsp;&bull; ✅&nbsp;Passed: 701<br>&nbsp;&nbsp;&bull; ⏭️&nbsp;Skipped: 0 | &bull; Python/WebSocket Live<br>&nbsp;&nbsp;&bull; ✅&nbsp;Passed: 128<br>&nbsp;&nbsp;&bull; ⏭️&nbsp;Skipped: 0<br>&bull; Browser E2E<br>&nbsp;&nbsp;&bull; ✅&nbsp;Passed: 68<br>&nbsp;&nbsp;&bull; ⏭️&nbsp;Skipped: 0 | Headless Chromium baked into the IJT Browser CI image |
| ⏭️ | Test Client | Live specification test harness against OPC UA server | ➖ Not Applicable | &bull; Smoke<br>&nbsp;&nbsp;&bull; ✅&nbsp;Passed: 10<br>&nbsp;&nbsp;&bull; ⏭️&nbsp;Skipped: 0<br>&bull; Specification Tests<br>&nbsp;&nbsp;&bull; ✅&nbsp;Passed: 920<br>&nbsp;&nbsp;&bull; ⏭️&nbsp;Skipped: 152 | Capability and diagnostic notes grouped below |
| ✅ | Console Client | Live Python client behavior and OPC UA security coverage against OPC UA server | &bull; ✅&nbsp;Passed: 78<br>&bull; ⏭️&nbsp;Skipped: 0 | &bull; ✅&nbsp;Passed: 18<br>&bull; ⏭️&nbsp;Skipped: 0 | No additional notes |
| ✅ | C# Client | Nightly xUnit live behavior and OPC UA security coverage against OPC UA server | &bull; ✅&nbsp;Passed: 82<br>&bull; ⏭️&nbsp;Skipped: 0 | &bull; ✅&nbsp;Passed: 110<br>&bull; ⏭️&nbsp;Skipped: 0 | Nightly baseline check |

---

<a id="system-specification-test-suites"></a>

### 📑 Specification Test Suites — 2 suites

| Suite | Port | Live Tests | Skipped | Notes |
|:------|-----:|----------:|--------:|:------|
| Test Client — Smoke sanity | 40462 | 10 ✅ | 0 | Server and namespace reachability |
| Test Client — Specification Tests | 40462 | 920 ✅ | 152 ⏭️ | Capability and diagnostic notes grouped below ([Skip Details](#system-skip-details)) |

---

<a id="system-skip-details"></a>

### ⏭️ Skip Details

_Each suite below is collapsed by default — click to inspect skip reasons._

Server capability gaps are listed in [CUs Needing Review](#system-cus-needing-review) above (112 skips folded out of diagnostics).

<details><summary><b>Test Tooling Limitations</b> — 3 skips</summary>

| Reason | Count |
|:-------|------:|
| TOOLING LIMITATION - asyncua AddNodes service call unavailable (The server does not support the requested service.(BadServiceUnsupported)); server-side rejection must be verified manually or with OPC  | 2 |
| TOOLING LIMITATION - asyncua DeleteNodes service call unavailable (The server does not support the requested service.(BadServiceUnsupported)); server-side rejection must be verified manually or with O | 1 |

</details>

<details><summary><b>Simulator Regression Limits</b> — 4 skips</summary>

| Reason | Count |
|:-------|------:|
| SIMULATOR REGRESSION LIMIT - SimulateBulkResults(simple_ok) rejected by the server with The request could not be processed because it specified too many operations.(BadTooManyOperations); this simulat | 1 |
| SIMULATOR REGRESSION LIMIT - SimulateBulkResults(multi_step_ok) rejected by the server with The request could not be processed because it specified too many operations.(BadTooManyOperations); this sim | 1 |
| SIMULATOR REGRESSION LIMIT - SimulateBulkEvents(6, 5) raised BadTooManyOperations — the simulator intentionally rejects overlapping or excessive bulk event operations to protect server stability. | 1 |
| SIMULATOR REGRESSION LIMIT - SimulateBulkEvents(29, 3) raised BadTooManyOperations — the simulator intentionally rejects overlapping or excessive bulk event operations to protect server stability. | 1 |

</details>

<details><summary><b>Other Diagnostics</b> — 1 skip</summary>

| Reason | Count |
|:-------|------:|
| No target-server counter workflow is configured | 1 |

</details>

---

### 🧭 Companion Spec Profile Notes

_These notes cover companion-spec profile areas that are intentionally outside the active server profile._

<details><summary><b>Companion Spec Profile Notes</b> — 32 skips</summary>

| Reason | Count |
|:-------|------:|
| COMPANION SPEC PROFILE NOTE - LifetimeCounters AddIn omitted because no real lifetime-variable data is available; MachineryLifetimeCounterType requires at least one &lt;LifetimeVariable&gt; (MandatoryPlaceh | 4 |
| COMPANION SPEC PROFILE NOTE - Optional JoiningProcessManagement method 'DeleteJoiningProcess' is absent; dedicated method CU tracks server support | 2 |
| COMPANION SPEC PROFILE NOTE - Optional JoiningProcessManagement method 'SendJoiningProcess' is absent; dedicated method CU tracks server support | 2 |
| COMPANION SPEC PROFILE NOTE - Optional JoiningProcessManagement method 'GetJoiningProcess' is absent; dedicated method CU tracks server support | 2 |
| COMPANION SPEC PROFILE NOTE - Optional JoiningProcessManagement method 'SetJoiningProcessMapping' is absent; dedicated method CU tracks server support | 2 |
| COMPANION SPEC PROFILE NOTE - Optional JoiningProcessManagement method 'GetJoiningProcessRevisionList' is absent; dedicated method CU tracks server support | 2 |
| COMPANION SPEC PROFILE NOTE - Optional AssetManagement method 'DisconnectAsset' is absent; dedicated method CU tracks server support | 1 |
| COMPANION SPEC PROFILE NOTE - Optional AssetManagement method 'ExecuteOperation' is absent; dedicated method CU tracks server support | 1 |
| COMPANION SPEC PROFILE NOTE - Optional AssetManagement method 'GetErrorInformation' is absent; dedicated method CU tracks server support | 1 |
| COMPANION SPEC PROFILE NOTE - Optional AssetManagement method 'RebootAsset' is absent; dedicated method CU tracks server support | 1 |
| COMPANION SPEC PROFILE NOTE - Optional AssetManagement method 'SetCalibration' is absent; dedicated method CU tracks server support | 1 |
| COMPANION SPEC PROFILE NOTE - Optional JointManagement method 'DeleteJointComponent' is absent; dedicated method CU tracks server support | 1 |
| COMPANION SPEC PROFILE NOTE - Optional JointManagement method 'DeleteJointDesign' is absent; dedicated method CU tracks server support | 1 |
| COMPANION SPEC PROFILE NOTE - Optional JointManagement method 'GetJointComponent' is absent; dedicated method CU tracks server support | 1 |
| COMPANION SPEC PROFILE NOTE - Optional JointManagement method 'GetJointComponentList' is absent; dedicated method CU tracks server support | 1 |
| COMPANION SPEC PROFILE NOTE - Optional JointManagement method 'GetJointDesign' is absent; dedicated method CU tracks server support | 1 |
| COMPANION SPEC PROFILE NOTE - Optional JointManagement method 'GetJointDesignList' is absent; dedicated method CU tracks server support | 1 |
| COMPANION SPEC PROFILE NOTE - Optional JointManagement method 'GetJointRevisionList' is absent; dedicated method CU tracks server support | 1 |
| COMPANION SPEC PROFILE NOTE - Optional JointManagement method 'SendJointComponent' is absent; dedicated method CU tracks server support | 1 |
| COMPANION SPEC PROFILE NOTE - Optional JointManagement method 'SendJointDesign' is absent; dedicated method CU tracks server support | 1 |
| COMPANION SPEC PROFILE NOTE - Monitoring.Notifications not exposed for controller(s) in this server profile: ['1:TighteningController'] | 1 |
| COMPANION SPEC PROFILE NOTE - Monitoring.MachineryItemState not exposed for controller(s) in this server profile: ['1:TighteningController'] | 1 |
| COMPANION SPEC PROFILE NOTE - Monitoring.Notifications not exposed for tool(s) in this server profile: ['1:TighteningTool'] | 1 |
| COMPANION SPEC PROFILE NOTE - Monitoring.MachineryItemState not exposed for tool(s) in this server profile: ['1:TighteningTool'] | 1 |

</details>

---

<a id="system-performance-benchmarks"></a>

### ⏱️ Performance Benchmarks — 2 benchmarks

| Benchmark | Samples | min (ms) | average (ms) | max (ms) | Target | Result |
|:----------|--------:|---------:|-------------:|---------:|:-------|:------:|
| Console Client — Result Transfer Time | 20 | 10.87 | 86.58 | 110.17 | Average &lt; 500 ms · 90% of samples &lt; 500 ms | ✅ Pass |
| IJT Performance Client — Result Latency Benchmark | 3 | 22.04 | 42.62 | 67.28 | Average &lt; 250 ms · 90% of samples &lt; 500 ms | ✅ Pass |

_TOTAL = end of joining operation → client callback. The visible table shows min, average, and max latency. The Pass/Fail gate also requires at least 90% of samples to stay below the target. Per-sample timing pipeline details are recorded in JUnit XML test artifacts._

---

<a id="system-performance-hotspots"></a>

### ⏱️ Performance Hotspots

<details><summary><b>Click to expand</b> — job, browser, C# and Test Client timing drilldown</summary>

> Source order: current workflow run jobs API first, then Web Client timing JSON, C# TRX artifacts, and Test Client JUnit durations when available. Missing timing data is omitted rather than estimated.

| Source | Item | Duration | Status |
|:-------|:-----|---------:|:-------|
| Workflow job | 🏁 Web Client - WebSocket API | 5.6 min | Passed ✅ |
| Workflow job | Console OPC UA Security - Windows | 5.5 min | Passed ✅ |
| Workflow job | Test Client - Windows Live (port 40462) | 5.2 min | Passed ✅ |
| Workflow job | C# OPC UA Security - Windows | 5.1 min | Passed ✅ |
| Workflow job | C# Client - Live Tests (port 40464) | 4.9 min | Passed ✅ |
| Workflow job | Web Client Browser - Browser Features (1/2) | 4.1 min | Passed ✅ |
| Browser timing artifact | Browser Features (1/2) | 3.2 min | Recorded 📊 |
| Workflow job | Web Client Browser - Browser Features (2/2) | 3.0 min | Passed ✅ |
| Workflow job | Web Client - Docker Tests | 2.9 min | Passed ✅ |
| Workflow job | Web Client - Direct OPC UA | 2.8 min | Passed ✅ |

#### Bottleneck Spotlight

> 🏁 **Web Client - WebSocket API** is the current longest reliable timing source (5.6 min, Workflow job).

<details><summary><b>Browser Feature Stage Timing</b></summary>

| Shard | Total | pip-install | npm-install | Playwright install | Playwright features | Other |
|:------|------:|------------:|------------:|-------------------:|--------------------:|------:|
| 1/2 | 3.2 min | 0.0 s | 2.9 s | 0.4 s | 2.9 min | 12.7 s |
| 2/2 | 2.3 min | 0.0 s | 2.9 s | 0.2 s | 2.0 min | 12.7 s |

</details>

<details><summary><b>C# Live Timing Details</b></summary>

| Class | Tests | Total | Avg | Max |
|:------|------:|------:|----:|----:|
| LiveIntegrationDetailedTests | 95 | 2.2 min | 1.4 s | 5.6 s |
| LiveIntegrationTests | 15 | 35.8 s | 2.4 s | 5.2 s |

#### Slowest C# Live Tests

| Test | Duration | Outcome |
|:-----|---------:|:--------|
| FullFlow_Subscribe_Trigger_EventReceived_GetLatestResult_ResultIdsMatch | 5.6 s | Passed |
| EventSubscription_ReceivesResultEvent_WithinTimeout | 5.2 s | Passed |
| Subscribe_ThenTriggerResult_EventArgs_EventTime_IsRecent | 5.2 s | Passed |
| SimulateEvent_ThenEventReceived_ViaSubscription | 5.2 s | Passed |
| Subscribe_ThenTriggerResult_EventArgs_Classification_IsNonEmpty | 5.1 s | Passed |
| Subscribe_ThenTriggerResult_EventArgs_AllFields_IsNonEmpty | 5.1 s | Passed |
| Subscribe_ThenTriggerResult_EventArgs_SequenceNumber_IsPositive | 5.1 s | Passed |
| Subscribe_ThenTriggerResult_EventArgs_ResultId_IsNonEmpty | 5.1 s | Passed |
| Subscribe_ThenTriggerSystemEvent_JoiningSystemEventArgs_ReceivedWithFields | 5.1 s | Passed |
| SimulateSingleResult_ThenResultReceived_ViaSubscription | 5.1 s | Passed |

</details>

<details><summary><b>Test Client Specification Test Timing Details</b></summary>

| Test | Duration | Outcome |
|:-----|---------:|:--------|
| test_bulk_events_exceeds_single_event_count | 30.5 s | Success |
| test_condition_disable_and_enable_methods_are_callable | 10.3 s | Success |
| test_request_results_populates_requested_result_variable | 6.3 s | Success |
| test_requested_result_variable_source_timestamp_is_set_after_request | 6.2 s | Success |
| test_request_results_consecutive_calls_handled_gracefully | 6.0 s | Success |
| test_send_identifier_methods_present_in_method_set[SendIdentifiers] | 5.3 s | Success |
| test_all_simulated_event_use_cases_raise_joining_system_events[asset_state-event_types0] | 5.0 s | Success |
| test_sync_result_has_sync_classification | 4.4 s | Success |
| test_condition_acknowledge_sets_acked_state | 4.3 s | Success |
| test_result_associated_entities_contains_controller_identifier | 4.2 s | Success |

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
| Image ref | `ghcr.io/umati/ua-for-industrial-joining-technologies/ijt-browser-ci@sha256:2eb95a9759277442d5aa75f09c8bef1190559ccb71da1b779d11a074724da170` |
| Inputs fingerprint | `aed2160a435459318085e79a147a9c158dcf2e1a315dcbce910fde314fb1d0e3` |

</details>

</details>

---

<a id="system-per-client-quick-index"></a>

### 📚 Per-Client Quick Index — 5 clients

| Client / Component | Appears In |
|:-------------------|:-----------|
| OPC UA Server | [Test Results](#system-test-results) · [Component Test Results](#system-component-test-results) · [Performance Hotspots](#system-performance-hotspots) |
| Web Client | [Test Results](#system-test-results) · [Component Test Results](#system-component-test-results) · [Performance Hotspots](#system-performance-hotspots) |
| Test Client | [Test Results](#system-test-results) · [Component Test Results](#system-component-test-results) · [Specification Test Suites](#system-specification-test-suites) · [Specification Test Report](#system-test-client-specification-test-report) · [Performance Hotspots](#system-performance-hotspots) |
| Console Client | [Test Results](#system-test-results) · [Component Test Results](#system-component-test-results) · [Performance Benchmarks](#system-performance-benchmarks) |
| C# Client | [Test Results](#system-test-results) · [Component Test Results](#system-component-test-results) · [Performance Hotspots](#system-performance-hotspots) |

---
Reports (no sign-in): [Runs](https://umati.github.io/UA-for-Industrial-Joining-Technologies/) · [CI](https://umati.github.io/UA-for-Industrial-Joining-Technologies/latest/ci/) · [System Tests](https://umati.github.io/UA-for-Industrial-Joining-Technologies/runs/42590909143/)
