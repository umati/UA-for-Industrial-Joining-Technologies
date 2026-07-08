# IJT Specification Test Report

🟢 **Passed** · **0 action items** · **Validation 100.0% (98/98)** · **Server support 79.7% (98/123)**

| Item | Value |
|---|---|
| **Server** | My IJT Server (`opc.tcp://fixture.ijt.test:40451`) |
| **Capability profile** | Full IJT Base Specification Coverage |
| **Run** | 2026-05-13 14:00 UTC · Duration 1m 25s |
| **Build** | commit `15bc900` · run logs: Not Applicable |

## 📊 Specification Test Overview

> 🚦 Review: 🔴 Failed · 🟠 Blocked · ⚪ Not Supported · ℹ️ With Notes

| Server Support Coverage | Validation Health | Specification Test Action Items | Server Scope Notes |
|:---:|:---:|:---:|:---:|
| **79.7%** | **100.0%** | **🔴 0 Failed · 🟠 0 Blocked** | **⚪ 25 Not Supported · ℹ️ 0 With Notes** |
| 98 / 123 CUs server-supported | 98 / 98 server-supported CUs validated | No action needed | Information only. Review scope and caveats |

<a id="system-cus-needing-review"></a>

## 📋 CUs Needing Review — 25 rows

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
| ⚪&nbsp;Not&nbsp;Supported | IJT Joint Design Data | No | Conformance unit 'IJT Joint Design Data' is not supported | 3 | 0 | 3 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Reboot Asset | No | Method 'RebootAsset' is not supported | 4 | 0 | 4 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Request Unacknowledged Results | No | Method 'RequestUnacknowledgedResults' is not supported | 7 | 0 | 7 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Send Joining Process | No | Method 'SendJoiningProcess' is not supported | 5 | 0 | 5 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Send Joint Component | No | Method 'SendJointComponent' is not supported | 6 | 0 | 6 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Send Joint Design | No | Method 'SendJointDesign' is not supported | 6 | 0 | 6 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Set Calibration | No | Method 'SetCalibration' is not supported | 4 | 0 | 4 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Set Joining Process Mapping | No | Method 'SetJoiningProcessMapping' is not supported | 3 | 0 | 3 | 0 | 0 |
| ⚪&nbsp;Not&nbsp;Supported | IJT Set Offline Timer | No | Method 'SetOfflineTimer' is not supported | 4 | 0 | 4 | 0 | 0 |

## 🧩 IJT Facet Support — 12 Supported · 5 Partial · 2 Not Supported

> 🚦 Support: ✅ Supported · ⚠️ Partially Supported · ⚪ Not Supported

_Auto-generated from the server profile and specification test outcomes. Full detail is in IJT Facet Breakdown._

- ⚪ **Joint Component** — Not Supported. Joint component send, list, read, data, and delete coverage.
- ⚪ **Joint Design** — Not Supported. Joint design send, list, read, data, and delete coverage.
- ⚠️ **Additional Asset Methods** — Partially Supported. Optional asset operation methods beyond the asset topology baseline.
- ⚠️ **Additional Process Methods** — Partially Supported. Optional joining process definition, mapping, counter, delete, and revision-list methods.
- ⚠️ **Asset Connection** — Partially Supported. Asset connection facet for DisconnectAsset and asset connection event coverage.
- ⚠️ **Joint** — Partially Supported. Joint management base object and methods for sending, listing, selecting, reading, deleting, and revising joints.
- ⚠️ **Stored Result** — Partially Supported. Stored/requested result workflows including result requests, requested-result access, acknowledgements, and unacknowledged-result requests.
- ✅ **Asset Management Assets** — Supported. Asset topology, asset identification, Machinery building blocks, health, service, calibration, and individual IJT asset type coverage.
- ✅ **Basic Joining System** — Supported. Minimum conformance requirement for any OPC UA IJT server: JoiningSystem structure, identification, and Machinery building blocks.
- ✅ **Batch Result** — Supported. Batch and intervention result support with related result counters.
- ✅ **Enable Tool** — Supported. EnableAsset/enable-tool workflow support and corresponding asset enable state event coverage.
- ✅ **Event Management** — Supported. Joining system event payload, condition classes, asset connection events, identifier events, process selection events, and event content fields.

_Showing the most relevant capability areas here. Full capability detail is in IJT Facet Breakdown. Capability area counts: 12 Supported · 5 Partially Supported · 2 Not Supported._

## 📐 IJT Facet Breakdown

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
| IJT Sequential Process Operations Server Facet | Facet | 4 | 4 | 100.0% | 100.0% | 🟢&nbsp;Supported: 4 | 🟢&nbsp;Supported |
| IJT Additional Process Methods Server Facet | Facet | 6 | 1 | 16.7% | 100.0% | 🟢&nbsp;Supported: 1<br>⚪&nbsp;Not&nbsp;Supported: 5 | 🟩&nbsp;Supported&nbsp;with&nbsp;Notes |
| IJT Joint Server Facet | Facet | 8 | 7 | 87.5% | 100.0% | 🟢&nbsp;Supported: 7<br>⚪&nbsp;Not&nbsp;Supported: 1 | 🟩&nbsp;Supported&nbsp;with&nbsp;Notes |
| IJT Joint Design Server Facet | Facet | 5 | 0 | 0.0% | Not Applicable | ⚪&nbsp;Not&nbsp;Supported: 5 | ⚪&nbsp;Not&nbsp;Supported |
| IJT Joint Component Server Facet | Facet | 5 | 0 | 0.0% | Not Applicable | ⚪&nbsp;Not&nbsp;Supported: 5 | ⚪&nbsp;Not&nbsp;Supported |
| Basic Joining System Server Facet | Facet | 3 | 3 | 100.0% | 100.0% | 🟢&nbsp;Supported: 3 | 🟢&nbsp;Supported |
| General Joining System Server Facet | Facet Group | 39 | 39 | 100.0% | 100.0% | 🟢&nbsp;Supported: 39 | 🟢&nbsp;Supported |
| Joining System Selectable Features Server Facet | Facet Group | 84 | 59 | 70.2% | 100.0% | 🟢&nbsp;Supported: 59<br>⚪&nbsp;Not&nbsp;Supported: 25 | 🟩&nbsp;Supported&nbsp;with&nbsp;Notes |

</details>

<details>
<summary><b>Test Client Environment</b></summary>

| Item | Value |
|---|---|
| Test Client commit | `15bc900` |
| Python | 3.14.3 |
| asyncua | 1.2b2 |
| Host OS | Windows-11-10.0.26200-SP0 |
| Repro command | `python run_all_tests.py` |
| Run logs | Not Applicable |

</details>

<details>
<summary><b>Skip &amp; Expected-Failure Diagnostics</b></summary>

_Diagnostic skip buckets and expected failures. The "Not Supported:" reasons are intentionally filtered here — server-unsupported CUs are tracked separately in "CUs Needing Review"._

#### Diagnostic Skips

_No diagnostic skips on this run._

</details>

---
## 📎 Report References

- Term reference: see [REPORT_GLOSSARY.md](OPC_UA_Clients/Release2/IJT_Test_Client/docs/REPORT_GLOSSARY.md) for definitions of report terms.
- Full detail: download `report.xlsx` or `report.html` from the run artifacts.