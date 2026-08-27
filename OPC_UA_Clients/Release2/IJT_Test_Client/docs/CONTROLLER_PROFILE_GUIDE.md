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

Keep real endpoints, ProductInstanceUris, process identifiers, serial numbers,
and unsanitized evidence in ignored private profiles.
