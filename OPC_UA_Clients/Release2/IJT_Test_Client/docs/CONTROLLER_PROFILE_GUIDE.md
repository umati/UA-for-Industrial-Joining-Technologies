# Controller Profile Guide

The IJT information model uses `JoiningProcess` as the generic process
abstraction. A controller can use it for a program, batch, job, sequence,
application recipe, or another technology-specific process. Do not encode a
vendor's process vocabulary into shared Test Client logic.

## Selection

Prefer this order:

1. `JoiningProcessId`
2. `JoiningProcessOriginId` when the server provides it
3. `SelectionName` only as an optional server-specific fallback

`SelectionName` can depend on controller configuration and should not be used
as the stable identity when process identifiers are available.

## Profile responsibilities

A server capability file declares implemented CUs. A target-server profile
declares one controlled execution workflow.

| Concern | Generic profile setting |
|---|---|
| Process identity | `selection.joining_process.joining_process_id` |
| Primary/final result | `single`, `sync`, `batch`, `job`, `stitching`, `intervention`, `text`, or `any` classification |
| Earlier result layers | Optional `intermediate_classifications`, such as `[batch]` before a final `job` result |
| Starts | `single_start_produces_final_result` or `one_start_per_operation` |
| State changes | Explicit `allowed_methods` only |
| Tool enablement | `extension_fields.enable_asset_policy`: `when_disabled` or `always` |
| Tool disablement | Denied unless `extension_fields.allow_disable_asset: true` |
| Intervention evidence | `extension_fields.intervention_method` plus explicit method permission |
| Controller readiness | Domain method status and status message |
| Identifiers | Verify `AssociatedEntities`; reset only when required |

For multi-operation workflows, the runner selects one `JoiningProcess`, starts
one operation, waits for its SingleResult completion signal, and only then
starts the next operation.

Result classification describes the evidence emitted by the workflow, not the
kind or vendor name of the selected `JoiningProcess`. The runner keeps CUs for
the primary classification and every declared intermediate classification. For
example, `classification: job` with `intermediate_classifications: [batch]`
tests both JobResult and BatchResult CUs. A fixtured-controller Job that emits
SyncResult instead uses `intermediate_classifications: [sync]`.

For a sequence that produces several result layers, configure its real operation
count and use `one_start_per_operation`. The reusable trigger subscribes before
starting, selects the generic `JoiningProcess`, waits for each correlated
SingleResult, and then starts the next operation. The same workflow can therefore
collect SingleResult, BatchResult, and final JobResult without encoding vendor
terms in shared code.

State-changing specification probes are blocked on real targets. Only configured
workflow adapters may invoke them. `EnableAsset(false)` additionally requires
argument-level opt-in and permitted disable probes restore `true` in `finally`.
For `EnableAsset(true)`, use `when_disabled` to monitor
`Tool.Parameters.Enabled`, or `always` when harmless reassertion is needed for a
controller's separate remote-readiness state.

Use the discovered Tool `ProductInstanceUri` for Tool-context operations:
identifier methods, enablement, joining-process discovery/selection/start,
counters, interventions, Tool I/O, and result-correlated workflows. Do not use
the Controller PIU as a convenient default for those calls. A Controller or
other asset PIU is appropriate only when the method applies to that asset or
when intentionally testing non-applicable-asset rejection. Empty or null PIU
belongs only in dedicated default-asset semantic tests.

An InterventionResult workflow uses the selected Tool PIU and
`JoiningProcessIdentification` plus method-specific arguments. Supported profile
actions include increment/decrement counters, reset, and abort. The action must
also appear in `state_changing_methods.allowed_methods`.

Unattended target runs must not synthesize events. If no deterministic event or
condition action is configured, those tests are skipped as not observed. Result
events are validated only when the configured joining workflow actually produces
a result.

Keep real endpoints, ProductInstanceUris, process identifiers, serial numbers,
and unsanitized evidence in ignored private profiles.

For copy commands, every field that must be reviewed, preflight, automated,
guided, and classification-only commands, see
`TARGET_SERVER_CU_QUICK_START.md`.
