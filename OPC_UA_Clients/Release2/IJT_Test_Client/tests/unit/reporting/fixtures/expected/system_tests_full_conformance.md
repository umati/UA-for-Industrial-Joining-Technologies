# IJT Conformance Test Report

🟢 **PASSED** · **Score: 94 / 100**

| Item | Value |
|---|---|
| **Server** | My IJT Server (`opc.tcp://fixture.ijt.test:40451`) |
| **Capability profile** | Full IJT Base Conformance |
| **Run** | 2026-05-13 14:00 UTC · Duration 1m 25s |
| **Build** | commit `15bc900` · run logs: n/a |

## Conformance Overview

| Server Support Coverage | ✅ Validation Health | Action Items | Informational Notes |
|:---:|:---:|:---:|:---:|
| **79.7%** | **100.0%** | **🔴 0 Failed · 🟠 0 Blocked** | **⚪ 25 Not Supported · ℹ️ 3 With Notes** |
| 98 / 123 CUs server-supported | 98 / 98 server-supported CUs validated | No action needed | Information only; review scope and caveats |

### Change Since Last Run (commit `2068e58`, 1 day ago)

- Score **94 → 94**
- Validation Health 100.0% → 100.0%
- Server Support Coverage 79.7% → 79.7%
- Review Items: 🆕 0 new · ✅ 0 resolved · ⚠️ 0 regressed

## Capability Support

_Auto-generated from the server profile and conformance outcomes. Full detail is in Facet and CU Coverage._

- ⚪ **Joint Component** — Not Supported. Joint component send, list, read, data, and delete coverage.
- ⚪ **Joint Design** — Not Supported. Joint design send, list, read, data, and delete coverage.
- ⚠️ **Additional Asset Methods** — Partially Supported. Optional asset operation methods beyond the asset topology baseline.
- ⚠️ **Additional Process Methods** — Partially Supported. Optional joining process definition, mapping, counter, delete, and revision-list methods.
- ⚠️ **Asset Connection** — Partially Supported. Asset connection facet for DisconnectAsset and asset connection event coverage.
- ⚠️ **Joining Process Base** — Partially Supported. JoiningProcessManagement base object and list access for joining process definitions.
- ⚠️ **Joint** — Partially Supported. Joint management base object and methods for sending, listing, selecting, reading, deleting, and revising joints.
- ⚠️ **Stored Result** — Partially Supported. Stored/requested result workflows including result requests, requested-result access, acknowledgements, and unacknowledged-result requests.
- ✅ **Asset Management Assets** — Supported. Asset topology, asset identification, Machinery building blocks, health, service, calibration, and individual IJT asset type coverage.
- ✅ **Basic Joining System** — Supported. Minimum conformance requirement for any OPC UA IJT server: JoiningSystem structure, identification, and Machinery building blocks.
- ✅ **Batch Result** — Supported. Batch and intervention result support with related result counters.
- ✅ **Enable Tool** — Supported. EnableAsset/enable-tool workflow support and corresponding asset enable state event coverage.

_Capability area counts: 11 Supported · 6 Partially Supported · 2 Not Supported._

<details open>
<summary><b>All capability areas</b></summary>

| Capability Area | Support | Scope |
|---|---|---|
| Joint Component | ⚪ Not Supported | Joint component send, list, read, data, and delete coverage. |
| Joint Design | ⚪ Not Supported | Joint design send, list, read, data, and delete coverage. |
| Additional Asset Methods | ⚠️ Partially Supported | Optional asset operation methods beyond the asset topology baseline. |
| Additional Process Methods | ⚠️ Partially Supported | Optional joining process definition, mapping, counter, delete, and revision-list methods. |
| Asset Connection | ⚠️ Partially Supported | Asset connection facet for DisconnectAsset and asset connection event coverage. |
| Joining Process Base | ⚠️ Partially Supported | JoiningProcessManagement base object and list access for joining process definitions. |
| Joint | ⚠️ Partially Supported | Joint management base object and methods for sending, listing, selecting, reading, deleting, and revising joints. |
| Stored Result | ⚠️ Partially Supported | Stored/requested result workflows including result requests, requested-result access, acknowledgements, and unacknowledged-result requests. |
| Asset Management Assets | ✅ Supported | Asset topology, asset identification, Machinery building blocks, health, service, calibration, and individual IJT asset type coverage. |
| Basic Joining System | ✅ Supported | Minimum conformance requirement for any OPC UA IJT server: JoiningSystem structure, identification, and Machinery building blocks. |
| Batch Result | ✅ Supported | Batch and intervention result support with related result counters. |
| Enable Tool | ✅ Supported | EnableAsset/enable-tool workflow support and corresponding asset enable state event coverage. |
| Event Management | ✅ Supported | Joining system event payload, condition classes, asset connection events, identifier events, process selection events, and event content fields. |
| General Process Operations | ✅ Supported | Selecting, starting, aborting, resetting, and reading the selected joining process. |
| Identifiers Methods | ✅ Supported | SendIdentifiers, GetIdentifiers, and ResetIdentifiers methods for attaching external entity identifiers to results. |
| Joining Result | ✅ Supported | Joining-result payload details such as failure reason, result values, step results, errors, and trace data. |
| Result | ✅ Supported | Result management baseline: result objects, result access methods, result event access, and basic result metadata. |
| Sequential Process Operations | ✅ Supported | Sequential joining process execution and process counter/size operations. |
| Sync Result | ✅ Supported | Synchronisation result support and related result counters. |

</details>

## Action Items

**🔴 0 Failed · 🟠 0 Blocked**

_No action items — server validation passed cleanly._

## Informational Notes

<details open>
<summary><b>Show informational notes</b></summary>

**⚪ 25 Not Supported · ℹ️ 3 With Notes**

| Review Status | CU | Outcome | Primary Reason |
|---|---|---|---|
| ⚪ Not Supported | IJT Acknowledge Results | ⚪ Not Supported | Not Supported: IJT Acknowledge Results - Method: AcknowledgeResults NOT SUPPORTED |
| ⚪ Not Supported | IJT Delete Joining Process | ⚪ Not Supported | Not Supported: IJT Delete Joining Process - Method: DeleteJoiningProcess NOT SUPPORTED |
| ⚪ Not Supported | IJT Delete Joint Component | ⚪ Not Supported | Not Supported: IJT Delete Joint Component - Method: DeleteJointComponent NOT SUPPORTED |
| ⚪ Not Supported | IJT Delete Joint Design | ⚪ Not Supported | Not Supported: IJT Delete Joint Design - Method: DeleteJointDesign NOT SUPPORTED |
| ⚪ Not Supported | IJT Disconnect Asset | ⚪ Not Supported | Not Supported: IJT Disconnect Asset - Method: DisconnectAsset NOT SUPPORTED |
| ⚪ Not Supported | IJT Execute Operation | ⚪ Not Supported | Not Supported: IJT Execute Operation - Method: ExecuteOperation NOT SUPPORTED |
| ⚪ Not Supported | IJT Feedback Methods | ⚪ Not Supported | Not Supported: IJT Feedback Methods - Methods: GetFeedbackFileList, SendFeedback NOT SUPPORTED |
| ⚪ Not Supported | IJT Get Error Information | ⚪ Not Supported | Not Supported: IJT Get Error Information - Method: GetErrorInformation NOT SUPPORTED |
| ⚪ Not Supported | IJT Get Joining Process | ⚪ Not Supported | Not Supported: IJT Get Joining Process - Method: GetJoiningProcess NOT SUPPORTED |
| ⚪ Not Supported | IJT Get Joining Process Revision List | ⚪ Not Supported | Not Supported: IJT Get Joining Process Revision List - Method: GetJoiningProcessRevisionList NOT SUPPORTED |
| … | … | … | 18 more items in Conformance Status |

</details>

<details>
<summary><b>Coverage Overview</b></summary>

_These rows separate the active server capability profile from reference IJT facet groups and the complete CU set._

| Coverage View | Purpose | Facets | CUs | Server Supported CUs | Server Support % | Supported CUs Validated % | Outcomes | Outcome |
|---|---|---:|---:|---:|---:|---:|---|---|
| Full IJT Base Conformance | Server capability profile | 21 | 123 | 98 | 79.7% | 100.0% | 95 Supported<br>3 With Notes<br>25 Not Supported<br>0 Blocked<br>0 Failed | 🟩 Supported with Notes |
| Basic Joining System Server Facet | Reference IJT facet | 1 | 3 | 3 | 100.0% | 100.0% | 3 Supported<br>0 With Notes<br>0 Not Supported<br>0 Blocked<br>0 Failed | 🟢 Supported |
| General Joining System Server Facet | Reference IJT facet | 1 | 39 | 39 | 100.0% | 100.0% | 37 Supported<br>2 With Notes<br>0 Not Supported<br>0 Blocked<br>0 Failed | 🟩 Supported with Notes |
| Joining System Selectable Features Server Facet | Reference IJT facet | 1 | 84 | 59 | 70.2% | 100.0% | 58 Supported<br>1 With Notes<br>25 Not Supported<br>0 Blocked<br>0 Failed | 🟩 Supported with Notes |

</details>

<details>
<summary><b>Facet and CU Coverage</b></summary>

| Facet | Type | CUs | Server Supported CUs | Server Support % | Supported CUs Validated % | Outcomes | Outcome |
|---|---|---:|---:|---:|---:|---|---|
| IJT Result Server Facet | Facet | 12 | 12 | 100.0% | 100.0% | 12 Supported<br>0 With Notes<br>0 Not Supported<br>0 Blocked<br>0 Failed | 🟢 Supported |
| IJT Joining Result Server Facet | Facet | 7 | 7 | 100.0% | 100.0% | 7 Supported<br>0 With Notes<br>0 Not Supported<br>0 Blocked<br>0 Failed | 🟢 Supported |
| IJT Sync Result Server Facet | Facet | 2 | 2 | 100.0% | 100.0% | 2 Supported<br>0 With Notes<br>0 Not Supported<br>0 Blocked<br>0 Failed | 🟢 Supported |
| IJT Batch Result Server Facet | Facet | 3 | 3 | 100.0% | 100.0% | 3 Supported<br>0 With Notes<br>0 Not Supported<br>0 Blocked<br>0 Failed | 🟢 Supported |
| IJT Stored Result Server Facet | Facet | 5 | 3 | 60.0% | 100.0% | 3 Supported<br>0 With Notes<br>2 Not Supported<br>0 Blocked<br>0 Failed | 🟩 Supported with Notes |
| IJT Asset Management Assets Server Facet | Facet | 23 | 23 | 100.0% | 100.0% | 23 Supported<br>0 With Notes<br>0 Not Supported<br>0 Blocked<br>0 Failed | 🟢 Supported |
| IJT Identifiers Methods Server Facet | Facet | 3 | 3 | 100.0% | 100.0% | 3 Supported<br>0 With Notes<br>0 Not Supported<br>0 Blocked<br>0 Failed | 🟢 Supported |
| IJT Additional Asset Methods Server Facet | Facet | 9 | 2 | 22.2% | 100.0% | 2 Supported<br>0 With Notes<br>7 Not Supported<br>0 Blocked<br>0 Failed | 🟩 Supported with Notes |
| IJT Event Management Server Facet | Facet | 8 | 8 | 100.0% | 100.0% | 8 Supported<br>0 With Notes<br>0 Not Supported<br>0 Blocked<br>0 Failed | 🟢 Supported |
| IJT Enable Tool Server Facet | Facet | 2 | 2 | 100.0% | 100.0% | 2 Supported<br>0 With Notes<br>0 Not Supported<br>0 Blocked<br>0 Failed | 🟢 Supported |
| IJT Asset Connection Server Facet | Facet | 3 | 2 | 66.7% | 100.0% | 2 Supported<br>0 With Notes<br>1 Not Supported<br>0 Blocked<br>0 Failed | 🟩 Supported with Notes |
| IJT Joining Process Base Server Facet | Facet | 2 | 2 | 100.0% | 100.0% | 1 Supported<br>1 With Notes<br>0 Not Supported<br>0 Blocked<br>0 Failed | 🟩 Supported with Notes |
| IJT General Process Operations Server Facet | Facet | 6 | 6 | 100.0% | 100.0% | 6 Supported<br>0 With Notes<br>0 Not Supported<br>0 Blocked<br>0 Failed | 🟢 Supported |
| IJT Sequential Process Operations Server Facet | Facet | 4 | 4 | 100.0% | 100.0% | 4 Supported<br>0 With Notes<br>0 Not Supported<br>0 Blocked<br>0 Failed | 🟢 Supported |
| IJT Additional Process Methods Server Facet | Facet | 6 | 1 | 16.7% | 100.0% | 1 Supported<br>0 With Notes<br>5 Not Supported<br>0 Blocked<br>0 Failed | 🟩 Supported with Notes |
| IJT Joint Server Facet | Facet | 8 | 7 | 87.5% | 100.0% | 6 Supported<br>1 With Notes<br>1 Not Supported<br>0 Blocked<br>0 Failed | 🟩 Supported with Notes |
| IJT Joint Design Server Facet | Facet | 5 | 0 | 0.0% | n/a | 0 Supported<br>0 With Notes<br>5 Not Supported<br>0 Blocked<br>0 Failed | 🟩 Supported with Notes |
| IJT Joint Component Server Facet | Facet | 5 | 0 | 0.0% | n/a | 0 Supported<br>0 With Notes<br>5 Not Supported<br>0 Blocked<br>0 Failed | 🟩 Supported with Notes |
| Basic Joining System Server Facet | Facet | 3 | 3 | 100.0% | 100.0% | 3 Supported<br>0 With Notes<br>0 Not Supported<br>0 Blocked<br>0 Failed | 🟢 Supported |
| General Joining System Server Facet | Facet Group | 39 | 39 | 100.0% | 100.0% | 37 Supported<br>2 With Notes<br>0 Not Supported<br>0 Blocked<br>0 Failed | 🟩 Supported with Notes |
| Joining System Selectable Features Server Facet | Facet Group | 84 | 59 | 70.2% | 100.0% | 58 Supported<br>1 With Notes<br>25 Not Supported<br>0 Blocked<br>0 Failed | 🟩 Supported with Notes |

</details>

<details>
<summary><b>Conformance Status</b></summary>

_Review-level detail for CUs that need explanation or follow-up: Supported with Notes, Not Supported, Blocked, or Failed. Skip buckets below are diagnostics._

| Review Status | CU | Facet(s) | Server Supported | Outcome | Primary Reason | Tests | Passed | Not Supported | Blocked | Failures |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|
| ⚪ Not Supported | IJT Acknowledge Results | IJT Stored Result Server Facet | No | ⚪ Not Supported | Not Supported: IJT Acknowledge Results - Method: AcknowledgeResults NOT SUPPORTED | 7 | 0 | 7 | 0 | 0 |
| ⚪ Not Supported | IJT Delete Joining Process | IJT Additional Process Methods Server Facet | No | ⚪ Not Supported | Not Supported: IJT Delete Joining Process - Method: DeleteJoiningProcess NOT SUPPORTED | 2 | 0 | 2 | 0 | 0 |
| ⚪ Not Supported | IJT Delete Joint Component | IJT Joint Component Server Facet | No | ⚪ Not Supported | Not Supported: IJT Delete Joint Component - Method: DeleteJointComponent NOT SUPPORTED | 3 | 0 | 3 | 0 | 0 |
| ⚪ Not Supported | IJT Delete Joint Design | IJT Joint Design Server Facet | No | ⚪ Not Supported | Not Supported: IJT Delete Joint Design - Method: DeleteJointDesign NOT SUPPORTED | 3 | 0 | 3 | 0 | 0 |
| ⚪ Not Supported | IJT Disconnect Asset | IJT Additional Asset Methods Server Facet, IJT Asset Connection Server Facet | No | ⚪ Not Supported | Not Supported: IJT Disconnect Asset - Method: DisconnectAsset NOT SUPPORTED | 4 | 0 | 4 | 0 | 0 |
| ⚪ Not Supported | IJT Execute Operation | IJT Additional Asset Methods Server Facet | No | ⚪ Not Supported | Not Supported: IJT Execute Operation - Method: ExecuteOperation NOT SUPPORTED | 4 | 0 | 4 | 0 | 0 |
| ⚪ Not Supported | IJT Feedback Methods | IJT Additional Asset Methods Server Facet | No | ⚪ Not Supported | Not Supported: IJT Feedback Methods - Methods: GetFeedbackFileList, SendFeedback NOT SUPPORTED | 6 | 0 | 6 | 0 | 0 |
| ⚪ Not Supported | IJT Get Error Information | IJT Additional Asset Methods Server Facet | No | ⚪ Not Supported | Not Supported: IJT Get Error Information - Method: GetErrorInformation NOT SUPPORTED | 4 | 0 | 4 | 0 | 0 |
| ⚪ Not Supported | IJT Get Joining Process | IJT Additional Process Methods Server Facet | No | ⚪ Not Supported | Not Supported: IJT Get Joining Process - Method: GetJoiningProcess NOT SUPPORTED | 5 | 0 | 5 | 0 | 0 |
| ⚪ Not Supported | IJT Get Joining Process Revision List | IJT Additional Process Methods Server Facet | No | ⚪ Not Supported | Not Supported: IJT Get Joining Process Revision List - Method: GetJoiningProcessRevisionList NOT SUPPORTED | 4 | 0 | 4 | 0 | 0 |
| ⚪ Not Supported | IJT Get Joint Component | IJT Joint Component Server Facet | No | ⚪ Not Supported | Not Supported: IJT Get Joint Component - Method: GetJointComponent NOT SUPPORTED | 5 | 0 | 5 | 0 | 0 |
| ⚪ Not Supported | IJT Get Joint Component List | IJT Joint Component Server Facet | No | ⚪ Not Supported | Not Supported: IJT Get Joint Component List - Method: GetJointComponentList NOT SUPPORTED | 4 | 0 | 4 | 0 | 0 |
| ⚪ Not Supported | IJT Get Joint Design | IJT Joint Design Server Facet | No | ⚪ Not Supported | Not Supported: IJT Get Joint Design - Method: GetJointDesign NOT SUPPORTED | 5 | 0 | 5 | 0 | 0 |
| ⚪ Not Supported | IJT Get Joint Design List | IJT Joint Design Server Facet | No | ⚪ Not Supported | Not Supported: IJT Get Joint Design List - Method: GetJointDesignList NOT SUPPORTED | 4 | 0 | 4 | 0 | 0 |
| ⚪ Not Supported | IJT Get Joint Revision List | IJT Joint Server Facet | No | ⚪ Not Supported | Not Supported: IJT Get Joint Revision List - Method: GetJointRevisionList NOT SUPPORTED | 5 | 0 | 5 | 0 | 0 |
| ⚪ Not Supported | IJT Joint Component Data | IJT Joint Component Server Facet | No | ⚪ Not Supported | Not Supported: IJT Joint Component Data NOT SUPPORTED | 4 | 0 | 4 | 0 | 0 |
| ⚪ Not Supported | IJT Joint Design Data | IJT Joint Design Server Facet | No | ⚪ Not Supported | Not Supported: IJT Joint Design Data NOT SUPPORTED | 3 | 0 | 3 | 0 | 0 |
| ⚪ Not Supported | IJT Reboot Asset | IJT Additional Asset Methods Server Facet | No | ⚪ Not Supported | Not Supported: IJT Reboot Asset - Method: RebootAsset NOT SUPPORTED | 4 | 0 | 4 | 0 | 0 |
| ⚪ Not Supported | IJT Request Unacknowledged Results | IJT Stored Result Server Facet | No | ⚪ Not Supported | Not Supported: IJT Request Unacknowledged Results - Method: RequestUnacknowledgedResults NOT SUPPORTED | 7 | 0 | 7 | 0 | 0 |
| ⚪ Not Supported | IJT Send Joining Process | IJT Additional Process Methods Server Facet | No | ⚪ Not Supported | Not Supported: IJT Send Joining Process - Method: SendJoiningProcess NOT SUPPORTED | 5 | 0 | 5 | 0 | 0 |
| ⚪ Not Supported | IJT Send Joint Component | IJT Joint Component Server Facet | No | ⚪ Not Supported | Not Supported: IJT Send Joint Component - Method: SendJointComponent NOT SUPPORTED | 6 | 0 | 6 | 0 | 0 |
| ⚪ Not Supported | IJT Send Joint Design | IJT Joint Design Server Facet | No | ⚪ Not Supported | Not Supported: IJT Send Joint Design - Method: SendJointDesign NOT SUPPORTED | 6 | 0 | 6 | 0 | 0 |
| ⚪ Not Supported | IJT Set Calibration | IJT Additional Asset Methods Server Facet | No | ⚪ Not Supported | Not Supported: IJT Set Calibration - Method: SetCalibration NOT SUPPORTED | 4 | 0 | 4 | 0 | 0 |
| ⚪ Not Supported | IJT Set Joining Process Mapping | IJT Additional Process Methods Server Facet | No | ⚪ Not Supported | Not Supported: IJT Set Joining Process Mapping - Method: SetJoiningProcessMapping NOT SUPPORTED | 3 | 0 | 3 | 0 | 0 |
| ⚪ Not Supported | IJT Set Offline Timer | IJT Additional Asset Methods Server Facet | No | ⚪ Not Supported | Not Supported: IJT Set Offline Timer - Method: SetOfflineTimer NOT SUPPORTED | 4 | 0 | 4 | 0 | 0 |
| ℹ️ With Notes | IJT Joining Process Management | IJT Joining Process Base Server Facet | Yes | 🟩 Supported with Notes | Not Supported: Optional method 'DeleteJoiningProcess': Not Supported — skipping | 37 | 27 | 10 | 0 | 0 |
| ℹ️ With Notes | IJT Joint Management | IJT Joint Server Facet | Yes | 🟩 Supported with Notes | Not Supported: Optional method 'DeleteJointComponent': Not Supported | 25 | 16 | 9 | 0 | 0 |
| ℹ️ With Notes | IJT Method Input Argument | General Joining System Server Facet | Yes | 🟩 Supported with Notes | Not Supported: DisconnectAsset: Not Supported — cannot validate method signature | 13 | 8 | 5 | 0 | 0 |

</details>

<details>
<summary><b>Full CU Coverage</b></summary>

| CU | Facet(s) | Server Supported | Outcome | Tests | Passed | Not Supported | Blocked | Failures | Workbook Cases |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| IJT Result Management | IJT Result Server Facet | Yes | 🟢 Supported | 13 | 13 | 0 | 0 | 0 | 11 |
| IJT Single Result | IJT Result Server Facet | Yes | 🟢 Supported | 5 | 5 | 0 | 0 | 0 | 14 |
| IJT Basic Result | IJT Result Server Facet | Yes | 🟢 Supported | 19 | 19 | 0 | 0 | 0 | 17 |
| IJT Result Event Access | IJT Result Server Facet | Yes | 🟢 Supported | 8 | 8 | 0 | 0 | 0 | 15 |
| IJT Result Processing Times | IJT Result Server Facet | Yes | 🟢 Supported | 8 | 8 | 0 | 0 | 0 | 13 |
| IJT Result Processing Times Durations | IJT Result Server Facet | Yes | 🟢 Supported | 10 | 10 | 0 | 0 | 0 | 13 |
| IJT Get Latest Result | IJT Result Server Facet | Yes | 🟢 Supported | 13 | 13 | 0 | 0 | 0 | 14 |
| IJT Get Result By ID | IJT Result Server Facet | Yes | 🟢 Supported | 11 | 11 | 0 | 0 | 0 | 13 |
| IJT Get Result With Filter Criteria | IJT Result Server Facet | Yes | 🟢 Supported | 2 | 2 | 0 | 0 | 0 | 18 |
| IJT Result Variable Access | IJT Result Server Facet | Yes | 🟢 Supported | 9 | 9 | 0 | 0 | 0 | 12 |
| IJT Result Additional Data | IJT Result Server Facet | Yes | 🟢 Supported | 8 | 8 | 0 | 0 | 0 | 14 |
| IJT Result Extended Meta Data | IJT Result Server Facet | Yes | 🟢 Supported | 4 | 4 | 0 | 0 | 0 | 12 |
| IJT Joining Result Failure Reason | IJT Joining Result Server Facet | Yes | 🟢 Supported | 1 | 1 | 0 | 0 | 0 | 11 |
| IJT Joining Result Overall Result Values | IJT Joining Result Server Facet | Yes | 🟢 Supported | 5 | 5 | 0 | 0 | 0 | 12 |
| IJT Joining Result Step Results | IJT Joining Result Server Facet | Yes | 🟢 Supported | 1 | 1 | 0 | 0 | 0 | 12 |
| IJT Joining Result Errors | IJT Joining Result Server Facet | Yes | 🟢 Supported | 1 | 1 | 0 | 0 | 0 | 11 |
| IJT Joining Result Trace | IJT Joining Result Server Facet | Yes | 🟢 Supported | 11 | 11 | 0 | 0 | 0 | 12 |
| IJT Result Value Trace Point Time Offset | IJT Joining Result Server Facet | Yes | 🟢 Supported | 6 | 6 | 0 | 0 | 0 | 10 |
| IJT Result Value Trace Point Index | IJT Joining Result Server Facet | Yes | 🟢 Supported | 7 | 7 | 0 | 0 | 0 | 10 |
| IJT Sync Result | IJT Sync Result Server Facet | Yes | 🟢 Supported | 7 | 7 | 0 | 0 | 0 | 11 |
| IJT Sync Result Counters | IJT Sync Result Server Facet | Yes | 🟢 Supported | 4 | 4 | 0 | 0 | 0 | 10 |
| IJT Batch Result | IJT Batch Result Server Facet | Yes | 🟢 Supported | 6 | 6 | 0 | 0 | 0 | 11 |
| IJT Batch Result Counters | IJT Batch Result Server Facet | Yes | 🟢 Supported | 4 | 4 | 0 | 0 | 0 | 11 |
| IJT Intervention Result | IJT Batch Result Server Facet | Yes | 🟢 Supported | 5 | 5 | 0 | 0 | 0 | 10 |
| IJT Request Results | IJT Stored Result Server Facet | Yes | 🟢 Supported | 8 | 8 | 0 | 0 | 0 | 9 |
| IJT Requested Result Variable Access | IJT Stored Result Server Facet | Yes | 🟢 Supported | 5 | 5 | 0 | 0 | 0 | 8 |
| IJT Requested Result Event Access | IJT Stored Result Server Facet | Yes | 🟢 Supported | 5 | 5 | 0 | 0 | 0 | 7 |
| IJT Acknowledge Results | IJT Stored Result Server Facet | No | ⚪ Not Supported | 7 | 0 | 7 | 0 | 0 | 7 |
| IJT Request Unacknowledged Results | IJT Stored Result Server Facet | No | ⚪ Not Supported | 7 | 0 | 7 | 0 | 0 | 7 |
| IJT Asset Management | IJT Asset Management Assets Server Facet | Yes | 🟢 Supported | 38 | 38 | 0 | 0 | 0 | 13 |
| IJT Asset Management Controller | IJT Asset Management Assets Server Facet | Yes | 🟢 Supported | 15 | 15 | 0 | 0 | 0 | 10 |
| IJT Asset Management Tool | IJT Asset Management Assets Server Facet | Yes | 🟢 Supported | 15 | 15 | 0 | 0 | 0 | 9 |
| IJT Asset Management Servo | IJT Asset Management Assets Server Facet | Yes | 🟢 Supported | 5 | 5 | 0 | 0 | 0 | 8 |
| IJT Asset Management Memory Device | IJT Asset Management Assets Server Facet | Yes | 🟢 Supported | 4 | 4 | 0 | 0 | 0 | 7 |
| IJT Asset Management Cable | IJT Asset Management Assets Server Facet | Yes | 🟢 Supported | 6 | 6 | 0 | 0 | 0 | 7 |
| IJT Asset Management Power Supply | IJT Asset Management Assets Server Facet | Yes | 🟢 Supported | 9 | 9 | 0 | 0 | 0 | 7 |
| IJT Asset Management Feeder | IJT Asset Management Assets Server Facet | Yes | 🟢 Supported | 8 | 8 | 0 | 0 | 0 | 7 |
| IJT Asset Management Battery | IJT Asset Management Assets Server Facet | Yes | 🟢 Supported | 10 | 10 | 0 | 0 | 0 | 7 |
| IJT Asset Management Sensor | IJT Asset Management Assets Server Facet | Yes | 🟢 Supported | 8 | 8 | 0 | 0 | 0 | 7 |
| IJT Asset Management Accessory | IJT Asset Management Assets Server Facet | Yes | 🟢 Supported | 5 | 5 | 0 | 0 | 0 | 7 |
| IJT Asset Management Software | IJT Asset Management Assets Server Facet | Yes | 🟢 Supported | 4 | 4 | 0 | 0 | 0 | 7 |
| IJT Asset Management Sub Component | IJT Asset Management Assets Server Facet | Yes | 🟢 Supported | 5 | 5 | 0 | 0 | 0 | 7 |
| IJT Asset Management Virtual Station | IJT Asset Management Assets Server Facet | Yes | 🟢 Supported | 2 | 2 | 0 | 0 | 0 | 8 |
| IJT Asset Management Operation Counters | IJT Asset Management Assets Server Facet | Yes | 🟢 Supported | 8 | 8 | 0 | 0 | 0 | 8 |
| IJT Asset Management Tool Operation Cycle Counter | IJT Asset Management Assets Server Facet | Yes | 🟢 Supported | 2 | 2 | 0 | 0 | 0 | 8 |
| IJT Asset Management Battery Operation Cycle Counter | IJT Asset Management Assets Server Facet | Yes | 🟢 Supported | 2 | 2 | 0 | 0 | 0 | 8 |
| IJT Asset Management Health | IJT Asset Management Assets Server Facet | Yes | 🟢 Supported | 6 | 6 | 0 | 0 | 0 | 9 |
| IJT Asset Management Monitoring Health | IJT Asset Management Assets Server Facet | Yes | 🟢 Supported | 4 | 4 | 0 | 0 | 0 | 8 |
| IJT Asset Management Service | IJT Asset Management Assets Server Facet | Yes | 🟢 Supported | 4 | 4 | 0 | 0 | 0 | 8 |
| IJT Asset Management Calibration | IJT Asset Management Assets Server Facet | Yes | 🟢 Supported | 6 | 6 | 0 | 0 | 0 | 9 |
| IJT Asset Management Additional Information | IJT Asset Management Assets Server Facet | Yes | 🟢 Supported | 8 | 8 | 0 | 0 | 0 | 9 |
| IJT Asset Management Machinery Building Blocks | IJT Asset Management Assets Server Facet | Yes | 🟢 Supported | 10 | 10 | 0 | 0 | 0 | 8 |
| IJT Send Identifiers | IJT Identifiers Methods Server Facet | Yes | 🟢 Supported | 13 | 13 | 0 | 0 | 0 | 8 |
| IJT Get Identifiers | IJT Identifiers Methods Server Facet | Yes | 🟢 Supported | 9 | 9 | 0 | 0 | 0 | 8 |
| IJT Reset Identifiers | IJT Identifiers Methods Server Facet | Yes | 🟢 Supported | 10 | 10 | 0 | 0 | 0 | 8 |
| IJT Disconnect Asset | IJT Additional Asset Methods Server Facet, IJT Asset Connection Server Facet | No | ⚪ Not Supported | 4 | 0 | 4 | 0 | 0 | 8 |
| IJT Set Calibration | IJT Additional Asset Methods Server Facet | No | ⚪ Not Supported | 4 | 0 | 4 | 0 | 0 | 9 |
| IJT Reboot Asset | IJT Additional Asset Methods Server Facet | No | ⚪ Not Supported | 4 | 0 | 4 | 0 | 0 | 7 |
| IJT Feedback Methods | IJT Additional Asset Methods Server Facet | No | ⚪ Not Supported | 6 | 0 | 6 | 0 | 0 | 7 |
| IJT Set Time | IJT Additional Asset Methods Server Facet | Yes | 🟢 Supported | 4 | 4 | 0 | 0 | 0 | 8 |
| IJT Set Offline Timer | IJT Additional Asset Methods Server Facet | No | ⚪ Not Supported | 4 | 0 | 4 | 0 | 0 | 8 |
| IJT IO Signals Methods | IJT Additional Asset Methods Server Facet | Yes | 🟢 Supported | 5 | 5 | 0 | 0 | 0 | 8 |
| IJT Get Error Information | IJT Additional Asset Methods Server Facet | No | ⚪ Not Supported | 4 | 0 | 4 | 0 | 0 | 7 |
| IJT Execute Operation | IJT Additional Asset Methods Server Facet | No | ⚪ Not Supported | 4 | 0 | 4 | 0 | 0 | 7 |
| IJT Event Payload | IJT Event Management Server Facet | Yes | 🟢 Supported | 39 | 39 | 0 | 0 | 0 | 9 |
| IJT Event Condition Classes | IJT Event Management Server Facet | Yes | 🟢 Supported | 30 | 30 | 0 | 0 | 0 | 9 |
| IJT Asset Connection Event | IJT Event Management Server Facet, IJT Asset Connection Server Facet | Yes | 🟢 Supported | 4 | 4 | 0 | 0 | 0 | 8 |
| IJT Asset Connection State Event | IJT Event Management Server Facet, IJT Asset Connection Server Facet | Yes | 🟢 Supported | 4 | 4 | 0 | 0 | 0 | 8 |
| IJT Event Payload Associated Entities | IJT Event Management Server Facet | Yes | 🟢 Supported | 5 | 5 | 0 | 0 | 0 | 8 |
| IJT Event Payload Reported Values | IJT Event Management Server Facet | Yes | 🟢 Supported | 5 | 5 | 0 | 0 | 0 | 8 |
| IJT Identifiers Event | IJT Event Management Server Facet | Yes | 🟢 Supported | 6 | 6 | 0 | 0 | 0 | 8 |
| IJT Select Process Event | IJT Event Management Server Facet | Yes | 🟢 Supported | 4 | 4 | 0 | 0 | 0 | 8 |
| IJT Enable Tool | IJT Enable Tool Server Facet | Yes | 🟢 Supported | 6 | 6 | 0 | 0 | 0 | 9 |
| IJT Asset Enable State Event | IJT Enable Tool Server Facet | Yes | 🟢 Supported | 4 | 4 | 0 | 0 | 0 | 8 |
| IJT Joining Process Management | IJT Joining Process Base Server Facet | Yes | 🟩 Supported with Notes | 37 | 27 | 10 | 0 | 0 | 9 |
| IJT Get Joining Process List | IJT Joining Process Base Server Facet | Yes | 🟢 Supported | 6 | 6 | 0 | 0 | 0 | 8 |
| IJT Abort Joining Process | IJT General Process Operations Server Facet | Yes | 🟢 Supported | 4 | 4 | 0 | 0 | 0 | 8 |
| IJT Start Selected Joining | IJT General Process Operations Server Facet | Yes | 🟢 Supported | 7 | 7 | 0 | 0 | 0 | 8 |
| IJT Select Joining Process | IJT General Process Operations Server Facet | Yes | 🟢 Supported | 4 | 4 | 0 | 0 | 0 | 8 |
| IJT Deselect Joining Process | IJT General Process Operations Server Facet | Yes | 🟢 Supported | 2 | 2 | 0 | 0 | 0 | 6 |
| IJT Reset Joining Process | IJT General Process Operations Server Facet | Yes | 🟢 Supported | 3 | 3 | 0 | 0 | 0 | 8 |
| IJT Get Selected Joining Program | IJT General Process Operations Server Facet | Yes | 🟢 Supported | 4 | 4 | 0 | 0 | 0 | 8 |
| IJT Increment Joining Process Counter | IJT Sequential Process Operations Server Facet | Yes | 🟢 Supported | 5 | 5 | 0 | 0 | 0 | 7 |
| IJT Decrement Joining Process Counter | IJT Sequential Process Operations Server Facet | Yes | 🟢 Supported | 5 | 5 | 0 | 0 | 0 | 6 |
| IJT Set Joining Process Size | IJT Sequential Process Operations Server Facet | Yes | 🟢 Supported | 3 | 3 | 0 | 0 | 0 | 7 |
| IJT Start Joining Process | IJT Sequential Process Operations Server Facet | Yes | 🟢 Supported | 2 | 2 | 0 | 0 | 0 | 7 |
| IJT Delete Joining Process | IJT Additional Process Methods Server Facet | No | ⚪ Not Supported | 2 | 0 | 2 | 0 | 0 | 7 |
| IJT Send Joining Process | IJT Additional Process Methods Server Facet | No | ⚪ Not Supported | 5 | 0 | 5 | 0 | 0 | 8 |
| IJT Get Joining Process | IJT Additional Process Methods Server Facet | No | ⚪ Not Supported | 5 | 0 | 5 | 0 | 0 | 8 |
| IJT Set Joining Process Counter | IJT Additional Process Methods Server Facet | Yes | 🟢 Supported | 4 | 4 | 0 | 0 | 0 | 7 |
| IJT Set Joining Process Mapping | IJT Additional Process Methods Server Facet | No | ⚪ Not Supported | 3 | 0 | 3 | 0 | 0 | 6 |
| IJT Get Joining Process Revision List | IJT Additional Process Methods Server Facet | No | ⚪ Not Supported | 4 | 0 | 4 | 0 | 0 | 7 |
| IJT Joint Management | IJT Joint Server Facet | Yes | 🟩 Supported with Notes | 25 | 16 | 9 | 0 | 0 | 9 |
| IJT Send Joint | IJT Joint Server Facet | Yes | 🟢 Supported | 8 | 8 | 0 | 0 | 0 | 9 |
| IJT Get Joint List | IJT Joint Server Facet | Yes | 🟢 Supported | 5 | 5 | 0 | 0 | 0 | 8 |
| IJT Select Joint | IJT Joint Server Facet | Yes | 🟢 Supported | 6 | 6 | 0 | 0 | 0 | 9 |
| IJT Get Joint | IJT Joint Server Facet | Yes | 🟢 Supported | 8 | 8 | 0 | 0 | 0 | 8 |
| IJT Joint Data | IJT Joint Server Facet | Yes | 🟢 Supported | 5 | 5 | 0 | 0 | 0 | 8 |
| IJT Delete Joint | IJT Joint Server Facet | Yes | 🟢 Supported | 7 | 7 | 0 | 0 | 0 | 7 |
| IJT Get Joint Revision List | IJT Joint Server Facet | No | ⚪ Not Supported | 5 | 0 | 5 | 0 | 0 | 8 |
| IJT Send Joint Design | IJT Joint Design Server Facet | No | ⚪ Not Supported | 6 | 0 | 6 | 0 | 0 | 9 |
| IJT Get Joint Design List | IJT Joint Design Server Facet | No | ⚪ Not Supported | 4 | 0 | 4 | 0 | 0 | 8 |
| IJT Get Joint Design | IJT Joint Design Server Facet | No | ⚪ Not Supported | 5 | 0 | 5 | 0 | 0 | 8 |
| IJT Joint Design Data | IJT Joint Design Server Facet | No | ⚪ Not Supported | 3 | 0 | 3 | 0 | 0 | 8 |
| IJT Delete Joint Design | IJT Joint Design Server Facet | No | ⚪ Not Supported | 3 | 0 | 3 | 0 | 0 | 7 |
| IJT Send Joint Component | IJT Joint Component Server Facet | No | ⚪ Not Supported | 6 | 0 | 6 | 0 | 0 | 9 |
| IJT Get Joint Component List | IJT Joint Component Server Facet | No | ⚪ Not Supported | 4 | 0 | 4 | 0 | 0 | 8 |
| IJT Get Joint Component | IJT Joint Component Server Facet | No | ⚪ Not Supported | 5 | 0 | 5 | 0 | 0 | 8 |
| IJT Joint Component Data | IJT Joint Component Server Facet | No | ⚪ Not Supported | 4 | 0 | 4 | 0 | 0 | 8 |
| IJT Delete Joint Component | IJT Joint Component Server Facet | No | ⚪ Not Supported | 3 | 0 | 3 | 0 | 0 | 7 |
| IJT Joining System Base | Basic Joining System Server Facet | Yes | 🟢 Supported | 13 | 13 | 0 | 0 | 0 | 15 |
| IJT Joining System Identification | Basic Joining System Server Facet | Yes | 🟢 Supported | 14 | 14 | 0 | 0 | 0 | 13 |
| IJT Joining System Machinery Building Blocks | Basic Joining System Server Facet | Yes | 🟢 Supported | 4 | 4 | 0 | 0 | 0 | 10 |
| IJT Result Internal Identifiers | General Joining System Server Facet | Yes | 🟢 Supported | 9 | 9 | 0 | 0 | 0 | 12 |
| IJT Result External Identifiers | General Joining System Server Facet | Yes | 🟢 Supported | 7 | 7 | 0 | 0 | 0 | 11 |
| IJT Result Content | General Joining System Server Facet | Yes | 🟢 Supported | 6 | 6 | 0 | 0 | 0 | 11 |
| IJT Method Input Argument | General Joining System Server Facet | Yes | 🟩 Supported with Notes | 13 | 8 | 5 | 0 | 0 | 10 |
| IJT Job Result | Joining System Selectable Features Server Facet | Yes | 🟢 Supported | 4 | 4 | 0 | 0 | 0 | 11 |
| IJT Result Value Final Tag | Joining System Selectable Features Server Facet | Yes | 🟢 Supported | 5 | 5 | 0 | 0 | 0 | 11 |
| IJT Self Contained Consolidated Result | Joining System Selectable Features Server Facet | Yes | 🟢 Supported | 8 | 8 | 0 | 0 | 0 | 11 |
| IJT Consolidated Result With References | Joining System Selectable Features Server Facet | Yes | 🟢 Supported | 5 | 5 | 0 | 0 | 0 | 10 |
| IJT Partial Consolidated Result | Joining System Selectable Features Server Facet | Yes | 🟢 Supported | 3 | 3 | 0 | 0 | 0 | 11 |
| IJT Engineering Units | Joining System Selectable Features Server Facet | Yes | 🟢 Supported | 12 | 10 | 0 | 0 | 0 | 10 |

</details>

<details>
<summary><b>Test Environment</b></summary>

| Item | Value |
|---|---|
| Test Client commit | `15bc900` |
| Python | 3.14.3 |
| asyncua | 1.2b2 |
| Host OS | Windows-11-10.0.26200-SP0 |
| Repro command | `python run_all_tests.py` |
| Run logs | n/a |

</details>

<details>
<summary><b>Glossary and Reading Guide</b></summary>

- **Server capability profile** is the active profile selected by the server capability YAML.
- **Reference IJT facet** and **Reference full CU set** rows are comparison views only; they are not extra pass/fail requirements.
- **Server Supported CUs** means the CUs listed as supported in the server capability file.
- **Server Support %** is the share of CUs in that row that the server says it supports.
- **Supported CUs Validated %** is the share of server-supported CUs that this run validated as Supported or Supported with Notes.
- **Score** is a 0–100 composite of `0.7 × Validation Health + 0.3 × Server Support Coverage`, capped at 50 if any **Failed** item exists and capped at 75 if any **Blocked** item exists.
- **Review Status** highlights follow-up work: Failed = failure or error, Blocked = missing runtime precondition, Not Supported = server-supported CU not supported, With Notes = supported with notes or outside server support.
- **Outcome** is the CU-level conformance classification for the current run.
- **Change** appears only when at least one row changed since `test-results/report-baseline.json`; unchanged rows are left blank.
- Failures and errors are reported as **Failed**.
- Skip reasons are listed later as diagnostics and may overlap with conformance status items.

</details>

<details>
<summary><b>Test result counts</b></summary>

| Status | Count | % |
|--------|------:|--:|
| ✅ Passed | **713** | 83% |
| ❌ Failed | **0** | 0% |
| ⏭️ Skipped | **140** | 16% |
| 🟡 Expected Fail | **0** | 0% |
| **Total** | **853** | 100% |

</details>

<details>
<summary><b>Skip Diagnostics</b></summary>

Diagnostic skip buckets from pytest. These may overlap with conformance status items and do not by themselves reduce CU compliance when the CU also has passing support coverage.

| Reason | Count |
|--------|------:|
| IJT Acknowledge Results - Method: AcknowledgeResults NOT SUPPORTED | 7 |
| IJT Request Unacknowledged Results - Method: RequestUnacknowledgedResults NOT SUPPORTED | 7 |
| IJT Feedback Methods - Methods: GetFeedbackFileList, SendFeedback NOT SUPPORTED | 6 |
| IJT Send Joint Design - Method: SendJointDesign NOT SUPPORTED | 6 |
| IJT Send Joint Component - Method: SendJointComponent NOT SUPPORTED | 6 |
| IJT Send Joining Process - Method: SendJoiningProcess NOT SUPPORTED | 5 |
| IJT Get Joining Process - Method: GetJoiningProcess NOT SUPPORTED | 5 |
| IJT Get Joint Design - Method: GetJointDesign NOT SUPPORTED | 5 |
| IJT Get Joint Component - Method: GetJointComponent NOT SUPPORTED | 5 |
| IJT Get Joint Revision List - Method: GetJointRevisionList NOT SUPPORTED | 5 |
| IJT Disconnect Asset - Method: DisconnectAsset NOT SUPPORTED | 4 |
| IJT Set Calibration - Method: SetCalibration NOT SUPPORTED | 4 |
| IJT Reboot Asset - Method: RebootAsset NOT SUPPORTED | 4 |
| IJT Get Error Information - Method: GetErrorInformation NOT SUPPORTED | 4 |
| IJT Execute Operation - Method: ExecuteOperation NOT SUPPORTED | 4 |
| IJT Set Offline Timer - Method: SetOfflineTimer NOT SUPPORTED | 4 |
| IJT Get Joining Process Revision List - Method: GetJoiningProcessRevisionList NOT SUPPORTED | 4 |
| IJT Get Joint Design List - Method: GetJointDesignList NOT SUPPORTED | 4 |
| IJT Get Joint Component List - Method: GetJointComponentList NOT SUPPORTED | 4 |
| IJT Joint Component Data NOT SUPPORTED | 4 |

</details>

---
*Full detail: download `report.xlsx` or `report.html` from the run artifacts.*