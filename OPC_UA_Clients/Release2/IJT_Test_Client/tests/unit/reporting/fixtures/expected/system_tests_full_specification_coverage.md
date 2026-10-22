# IJT Specification Test Report

🟢 **Passed** · **0 action items** · **Validation 100.0% (98/98)** · **Server support 79.7% (98/123)**

| Item | Value |
|---|---|
| **Server** | Fixture IJT Server (`opc.tcp://fixture.ijt.test:40451`) |
| **Capability profile** | Full IJT Base Specification Coverage |
| **Run** | 2026-05-13 14:00 UTC · Duration 1m 25s |
| **Build** | commit `15bc900` · run logs: Not Applicable |

## 📊 Specification Test Overview

> 🚦 Review: 🔴 Failed · 🟠 Blocked · ⚪ Not Supported · ℹ️ With Notes

| Server Support Coverage | Validation Health | Specification Test Action Items | Server Scope Notes |
|:---:|:---:|:---:|:---:|
| **79.7%** | **100.0%** | **🔴 0 Failed · 🟠 0 Blocked** | **⚪ 25 Not Supported · ℹ️ 0 With Notes** |
| 98 / 123 CUs server-supported | 98 / 98 server-supported CUs validated | No action needed | Information only. Review scope and caveats |

**Live tests (unique):** 853 — 713 passed · 0 failed · 0 errors · 140 skipped · **CU-marked:** 850 (3 without CU marker) · **CUs (123):** 98 exercised · 25 skipped only · 0 not run · 0 without tests

<details>
<summary><b>Per-CU test counts</b> — 123 CUs, 850 CU-marked tests, 882 CU test links</summary>

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
| IJT Asset Management Battery | Exercised | 10 | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
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
| IJT Basic Result | Exercised | 19 | 19 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Batch Result | Exercised | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Batch Result Counters | Exercised | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Consolidated Result With References | Exercised | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Decrement Joining Process Counter | Exercised | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Delete Joining Process | Skipped only | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 |
| IJT Delete Joint | Exercised | 7 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Delete Joint Component | Skipped only | 3 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 |
| IJT Delete Joint Design | Skipped only | 3 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 |
| IJT Deselect Joining Process | Exercised | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Disconnect Asset | Skipped only | 4 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 |
| IJT Enable Tool | Exercised | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| IJT Engineering Units | Exercised | 12 | 12 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
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
| IJT Increment Joining Process Counter | Exercised | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
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
| IJT Joint Design Data | Skipped only | 3 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 |
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
| IJT Send Identifiers | Exercised | 13 | 13 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
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
| IJT Acknowledge Results | 7 | Not Supported (7): IJT Acknowledge Results - Method: AcknowledgeResults NOT SUPPORTED - CU: acknowledge_results. To enable: add it under c… |
| IJT Delete Joining Process | 2 | Not Supported (2): IJT Delete Joining Process - Method: DeleteJoiningProcess NOT SUPPORTED - CU: delete_joining_process. To enable: add it… |
| IJT Delete Joint Component | 3 | Not Supported (3): IJT Delete Joint Component - Method: DeleteJointComponent NOT SUPPORTED - CU: delete_joint_component. To enable: add it… |
| IJT Delete Joint Design | 3 | Not Supported (3): IJT Delete Joint Design - Method: DeleteJointDesign NOT SUPPORTED - CU: delete_joint_design. To enable: add it under cu… |
| IJT Disconnect Asset | 4 | Not Supported (4): IJT Disconnect Asset - Method: DisconnectAsset NOT SUPPORTED - CU: disconnect_asset. To enable: add it under cu_overrid… |
| IJT Execute Operation | 4 | Not Supported (4): IJT Execute Operation - Method: ExecuteOperation NOT SUPPORTED - CU: execute_operation. To enable: add it under cu_over… |
| IJT Feedback Methods | 6 | Not Supported (6): IJT Feedback Methods - Methods: GetFeedbackFileList, SendFeedback NOT SUPPORTED - CU: feedback_methods. To enable: add … |
| IJT Get Error Information | 4 | Not Supported (4): IJT Get Error Information - Method: GetErrorInformation NOT SUPPORTED - CU: get_error_information. To enable: add it un… |
| IJT Get Joining Process | 5 | Not Supported (5): IJT Get Joining Process - Method: GetJoiningProcess NOT SUPPORTED - CU: get_joining_process. To enable: add it under cu… |
| IJT Get Joining Process Revision List | 4 | Not Supported (4): IJT Get Joining Process Revision List - Method: GetJoiningProcessRevisionList NOT SUPPORTED - CU: get_joining_process_r… |
| IJT Get Joint Component | 5 | Not Supported (5): IJT Get Joint Component - Method: GetJointComponent NOT SUPPORTED - CU: get_joint_component. To enable: add it under cu… |
| IJT Get Joint Component List | 4 | Not Supported (4): IJT Get Joint Component List - Method: GetJointComponentList NOT SUPPORTED - CU: get_joint_component_list. To enable: a… |
| IJT Get Joint Design | 5 | Not Supported (5): IJT Get Joint Design - Method: GetJointDesign NOT SUPPORTED - CU: get_joint_design. To enable: add it under cu_override… |
| IJT Get Joint Design List | 4 | Not Supported (4): IJT Get Joint Design List - Method: GetJointDesignList NOT SUPPORTED - CU: get_joint_design_list. To enable: add it und… |
| IJT Get Joint Revision List | 5 | Not Supported (5): IJT Get Joint Revision List - Method: GetJointRevisionList NOT SUPPORTED - CU: get_joint_revision_list. To enable: add … |
| IJT Joint Component Data | 4 | Not Supported (4): IJT Joint Component Data NOT SUPPORTED - CU: joint_component_data. To enable: add it under cu_overrides in server_capab… |
| IJT Joint Design Data | 3 | Not Supported (3): IJT Joint Design Data NOT SUPPORTED - CU: joint_design_data. To enable: add it under cu_overrides in server_capabilitie… |
| IJT Reboot Asset | 4 | Not Supported (4): IJT Reboot Asset - Method: RebootAsset NOT SUPPORTED - CU: reboot_asset. To enable: add it under cu_overrides in server… |
| IJT Request Unacknowledged Results | 7 | Not Supported (7): IJT Request Unacknowledged Results - Method: RequestUnacknowledgedResults NOT SUPPORTED - CU: request_unacknowledged_re… |
| IJT Send Joining Process | 5 | Not Supported (5): IJT Send Joining Process - Method: SendJoiningProcess NOT SUPPORTED - CU: send_joining_process. To enable: add it under… |
| IJT Send Joint Component | 6 | Not Supported (6): IJT Send Joint Component - Method: SendJointComponent NOT SUPPORTED - CU: send_joint_component. To enable: add it under… |
| IJT Send Joint Design | 6 | Not Supported (6): IJT Send Joint Design - Method: SendJointDesign NOT SUPPORTED - CU: send_joint_design. To enable: add it under cu_overr… |
| IJT Set Calibration | 4 | Not Supported (4): IJT Set Calibration - Method: SetCalibration NOT SUPPORTED - CU: set_calibration. To enable: add it under cu_overrides … |
| IJT Set Joining Process Mapping | 3 | Not Supported (3): IJT Set Joining Process Mapping - Method: SetJoiningProcessMapping NOT SUPPORTED - CU: set_joining_process_mapping. To … |
| IJT Set Offline Timer | 4 | Not Supported (4): IJT Set Offline Timer - Method: SetOfflineTimer NOT SUPPORTED - CU: set_offline_timer. To enable: add it under cu_overr… |

</details>

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
| asyncua | 2.0.1 |
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