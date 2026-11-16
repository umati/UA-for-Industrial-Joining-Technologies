# Target Server CU Guide

> **Canonical entry point:** `python run_all_tests.py` (see options below).
> The simulator and a Target Server are both "OPC UA Servers Under Test" running
> the identical `specification_tests/` suite; a profile only controls
> applicability, safety, triggers, scoring, and evidence — never a separate
> test suite. Default (no flags) runs everything; `--phase2` runs
> specification_tests only; `--profile` controls Target Server execution.

---

## Stable Subcommands (recommended)

```bash
# Full run against a controller
python run_all_tests.py run --profile target_server_cu_profiles/controller.local.sut.yaml

# Read-only server inspection (no joining or configuration changes)
python run_all_tests.py inspect --endpoint opc.tcp://<host>:40451
python run_all_tests.py inspect --profile target_server_cu_profiles/controller.local.sut.yaml

# Generate a pre-filled manifest from a live server
python run_all_tests.py init-profile --endpoint opc.tcp://<host>:40451 --output target_server_cu_profiles/controller.local.sut.yaml

# Repair stale exact process references in an existing local manifest
python run_all_tests.py refresh-profile --profile target_server_cu_profiles/controller.local.sut.yaml
```

All existing flags from `run_all_tests.py` still work unchanged.
`refresh-profile` is an interactive local-configuration operation, not a test run.

---

## 1) Overview & Architecture

### What this is in simple words
The **IJT Test Client** verifies whether an OPC UA IJT Server adheres to the OPC 40450-1 specification correctly.
It does **not** replace a simulator — it provides formal, repeatable conformance testing.

- **Simulator** = functional behavior and reference implementation testing
- **IJT Test Client** = formal specification Conformance Unit (CU) testing

### What "123 CUs" means
- The project is built around **123 official IJT Conformance Units (CUs)** defined in OPC UA IJT Release 2.0.
- The test framework and CU reporting classify each CU (e.g. `Supported/Pass`, `Not Supported`, `Blocked`, `Failed`, `Environment/Error`) on every run.
- Goal: **All applicable CUs executed and clearly classified** on every run.

### Test suite organization
The test structure mirrors the specification chapters:
- `specification_tests/` = main specification test suite container
- Domain modules include `test_result_*.py`, `test_asset_*.py`, `test_joining_process.py`, `test_joint_management.py`, and `test_events.py`.

---

## 2) Auto-discover Tools and Processes

### Which YAML file controls what

Supply one complete SUT manifest from `target_server_cu_profiles/` or an ignored
local copy. The separate `profiles/` files are specification capability bundles
and a facet catalogue, not additional runtime manifests.
Generated SUTs use `capability_claims.cu_scope_policy: explicit`, so their
`cu_overrides` rows alone define claimed scope. `active_profile` and
`supported_facets` do not expand that table. Older manifests default to
`inherit`, where the profile and facets add groups before overrides apply.
Claims define scope, not physical permissions or proof of compliance.

Keep common field comments and ordering aligned, but preserve real differences
in identity, claims, permitted methods/risks and bounded result windows.
`Schema default` means the value used when omitted, not the value every example
must choose. [Profile maintenance](../target_server_cu_profiles/README.md#keep-portable-and-local-profiles-aligned)
describes the offline `--format-local` command, which consolidates verified
schema prose and aligns field order without changing YAML values or owner notes.

Keep past run dates and observations in project records or run reports, not
beside current settings. A support declaration is not evidence that the current
firmware passed. Combined results can contain child references or inline child
results, depending on the declared capability. Neither form belongs exclusively
to controllers or simulators.

**Tool selection is separate from process selection.** When
`workflows.tool_selector.product_instance_uri` is empty, `workflows.tool_selector.policy`
controls runtime Tool discovery:
- `first_ready` (default): selects the first Connected and Enabled Tool in
  deterministic `(BrowseName, ProductInstanceUri)` order, preferring Tools that
  advertise joining processes when several Tools are ready.
- `first_available`: selects the first Tool with a unique `ProductInstanceUri`
  in deterministic `(BrowseName, ProductInstanceUri)` order regardless of
  `Connected`/`Enabled` state.
- `discover_unique`: auto-selects only when a single Tool Object exists on the
  server; blocks when several Tools exist without an explicit `product_instance_uri`.
- `exact_match`: always requires `product_instance_uri` to be configured and
  matches only that Tool.

An explicit `product_instance_uri` always takes precedence and must match one
Tool. Automatic process discovery still resolves current process IDs within the
selected Tool scope.

In unattended `automated` runs (`execution_policy.allow_manual_steps: false`),
CUs declared `manual_required` (such as physical cable unplug/replug or physical
hardware fault conditions) are recorded under `manual_deferred_cus` rather than
blocking `supported` qualification when zero failures occur; in `guided` runs
(`allow_manual_steps: true`), `manual_required` CUs remain required for operator
verification.

### Repeat runs without updating process IDs

Configure intent once, then run the same command after programs are recreated:

```powershell
python -B .\run_all_tests.py run --profile .\target_server_cu_profiles\controller.local.sut.yaml
```

Automatic mode uses standard `GetJoiningProcessList` metadata and the current
process ID, not a vendor-specific name. Example settings:

```yaml
workflows:
  allow_discovered_processes: true
  max_candidates: 3
  max_total_start_invocations: 6
  process_selector:
    policy: first_compatible
    identifier_strategy: id_only
execution_policy:
  counter_effects:
    - method: IncrementJoiningProcessCounter
      count: 1
      process_policy: discover_unique
      process_classification: job
      identifier_strategy: id_only
      expected_result_classification: batch
```

This fragment supplements a reviewed manifest. Existing method and workflow
approvals are still required. It is not permission to run a production controller.

| Setting | Meaning |
|---|---|
| `first_compatible` | Try bounded compatible candidates using fresh IDs. Observed results, not catalog metadata, prove capability |
| `allow_discovered_processes: true` | Approve compatible processes within the reviewed Tool scope as physical workflow candidates |
| `exact_match` | Honour the configured ID, origin ID or optional SelectionName. Never substitute another target |
| `discover_unique` | Requires discovery approval and `id_only` or `id_with_origin`. Resolve exactly one process of the stated standard classification, respecting exact restrictions |
| `max_total_start_invocations` | Cap attempted starts across all candidates in one workflow, including failed/uncertain calls |

Missing or ambiguous counter targets block that workflow without a mutation.
Identity and catalog are checked again before the counter call. An attempted
counter effect is never retried in the same run. With `evidence_reuse.enabled`,
complete matching immutable evidence may serve other assertions in that run.
Completed counter evidence can be reused by the same trigger or a reader
without a new subscriber. Tool, current catalog, names, selected process and
structured configuration snapshots must still match. A fresh mutation always
requires its own subscriber. Legacy intervention without `counter_effects`
remains one-shot and does not provide the complete reusable capture contract.
Physical workflows require serial execution and an exclusively controlled test
environment. OPC UA calls are not transactional, so these checks cannot prevent
every concurrent external state change.

### Evidence acquisition without implicit authority

A fresh counter baseline is observed before the counter RPC. If passive
observation cannot supply it, `start_selected_joining` mode can acquire it through
an owned joining start only when the Start method and remote-start workflow are
already approved. That start consumes the existing process and total ceilings.
No selector value or CounterType is guessed to force the route to qualify.

The isolated counter delta is assessed before any further joining starts.
If the SUT only publishes an update after another joining operation, that update
cannot substitute for the missing isolated experiment. The counter obligation
remains INCOMPLETE. An attributable owned parent may still be completed under
existing authority, without repeating the counter mutation or raising a ceiling.
Missing baseline metadata likewise cannot silently leave an owned setup process
active when its normal completion is provable within the authorized budget.

GetSelectedJoiningProgram acquisition first uses current advertised Program
evidence. When necessary, it can perform one approved Program-specific selection,
never a joining start. Callable counter checks use the declared counter-effect
route rather than bypassing the direct-method guard. Other legacy probes remain
guarded when no approved route exists.

An incomplete PIU exposure proof, such as a remote reference or unavailable
PIU value, is a structured blocked prerequisite. Transport failures and invalid
client arguments are not silently converted into unavailable SUT support.

### Owned compound-result correlation

A child SingleResult identifies its executed Program, not necessarily the
selected Job. The collector reconstructs ownership through child references,
inline result envelopes, or explicit `PARENT_TYPE` (40) associated-result IDs.
An already observed owned Job can establish ancestry for later fresh children.
The server need not repeat the same partial Job notification after every start.

Retained ancestry is not fresh operation evidence. Each new start requires a
new completed SingleResult in its action window, from the selected Tool.
Previously observed operations, completed/aborted parents, foreign ownership
and pre-reset ancestry cannot authorize another start or settle a restart.
Loss of events still prohibits further actuation.
Counter baselines and affected Batch results use the same ownership proof.
The isolated counter assessment remains separate from natural parent completion.
An observed invalid delta remains FAILED after safe settlement. Missing isolated
updates remain INCOMPLETE, and neither outcome permits a counter retry.

### Completion, observation and unfinished process state

Start limits are safety ceilings, not expected Batch or Job sizes. A completed
SingleResult confirms one operation, not completion of its compound process.
The classification ceiling follows the selected parent's terminal classification,
not the requested child classification. A Job requested for SingleResult evidence
still uses the Job ceiling, bounded by the unchanged workflow and total ceilings.
Exhausting any applicable ceiling leaves missing evidence INCOMPLETE.
After the final permitted start, the subscription retains its independent
result-completion window, bounded by the overall workflow deadline. No additional
start is issued merely to obtain a late consolidated result.

An owned, non-partial parent result in COMPLETED (1), ABORTED (3), or FAILED (4)
ends collection and prevents another start. Its state is then checked against
`workflows.expected_results.expected_terminal_result_state`; the default remains
COMPLETED. An unexpected terminal state is a workflow failure, not a missing-result
timeout. The actual
parent, captured children and reference diagnostics remain available, including
a completed Batch when its parent Job failed.

This same rule applies to counter baseline/completion and abort/reset workflows.
A failed InterventionResult is retained as a counter failure; it does not prove
that the parent finished. A terminal failure is never cached as successful
workflow evidence. Dependent mutations do not repeat the failed experiment in
the same run. Missing operation evidence after an additional accepted start,
or event loss, still leaves settlement unproven and blocks further mutations.
No automatic reset, abort, cross-run state gate, or additional YAML option is
introduced.

Parent progression collection applies the selected Tool/process predicate.
Other envelopes remain archived for explicit child-reference resolution and
diagnostics, but an unrelated terminal result cannot complete the selected parent.
The action journal includes scenario identity, observed result identities,
classification, partial/state fields, associated entities, references, duplicate
flags and identity-rejection reasons.

Intermediate operation evidence needs selected-process attribution or an observed
parent-to-child result relationship. Tool identity alone does not authorize another
start, abort or reset. A repeated ResultId cannot confirm another start, even with
a different EventId. Missing identity or lost events stop further actuation.

### Controller-specific AssociatedEntities expectations

The optional `workflows.expected_results.associated_entities` list supplements
specification assertions. It does not replace them or change workflow ownership.
Omit it (or use `[]`) to retain existing behavior. For example:

```yaml
workflows:
  expected_results:
    associated_entities:
      - classification: single
        context: joining
        required: [TOOL]
        optional: [MEMORY_DEVICE, VIRTUAL_STATION]
        at_least_one_of: [PROGRAM, JOINING_PROCESS]
      - classification: intervention
        context: counter_intervention
        optional: [TOOL]
```

`classification` uses the existing result names. `context` defaults to `any`;
the other choices are `joining` and `counter_intervention`. Lists default to
empty. Rules are additive: an optional declaration never negates a required
declaration in another matching rule. Missing optional entities are allowed,
but configured entities present in a result must have non-empty EntityIds.
Extra entity types are allowed and existing specification validators still
apply. Full inline envelopes are checked; child-reference stubs are not asked
to contain complete identities. Unknown fields, names and conflicting
required/optional declarations in one rule are configuration errors.

Marking TOOL optional for a counter result is not an ownership waiver. A result
can satisfy that configured expectation yet remain unattributed, so the counter
workflow remains inconclusive and cannot authorize another automatic mutation.
No vendor-specific reporting requirement is silently inferred from the adapter implementation.

The remote-start preset includes editable entity expectations: TOOL is required
on joining Singles and optional on counter-only Intervention, Batch and Job
updates. These are preset choices, not universal specification requirements.
An installation can additionally require VIRTUAL_STATION on its counter updates.

For counter correlation, `workflows.tool_selector.virtual_station_product_instance_uri`
optionally pins the VirtualStation belonging to a configured Tool
`product_instance_uri`. Leave it empty (the default with `policy: first_ready`)
to auto-discover the VirtualStation from Tool- and process-owned joining results
or a unique VirtualStation on the server. Tool-less counter results must still
identify that station and the selected process, directly or through owned parent
references. A contradictory Tool, another station or another process is not
accepted. Fresh ResultIds, Intervention references, counter-delta checks and
existing start ceilings remain unchanged. Only counter workflow correlation uses
this fallback; joining operation evidence still requires the selected Tool.

`execution_policy.counter_effects[].verify_delta: true` makes the first consumer
qualify the complete counter experiment, including baseline, delta and owned
process completion, whether it requests a method check or InterventionResult.
Later consumers reuse the same experiment. The remote-start preset enables
this to avoid test-order-dependent unfinished Jobs.
It uses existing joining-start approvals and ceilings, not extra permissions
or retries. Omitted/false preserves legacy method-only behavior.

Profile settings select the evidence to check; they do not correct values published
by the server. `counter_type` and the optional exact `counter_name` select a counter
within the affected result classification. Leaving `counter_name` empty avoids
depending on display-name capitalization, but the selected counter must still be
unique. Result metadata names and descriptions are not counter selectors.
The same CounterType can occur at different result layers, so a job-wide tally
must not be substituted for an affected Batch counter. A display-name change
between firmware versions does not establish a semantic change; within one
experiment, the before/after counter identity must remain unchanged.
Setting `verify_delta: false` does not waive the dedicated counter-delta test,
which explicitly requests before/after verification. A method or InterventionResult
check can succeed while the server's published counter value is wrong; that is not
proof that the counter-effect qualification passed.
Keep an incorrect published delta as a failure. A YAML workaround that drops
the failing obligation is not a successful qualification of that behavior.

When a fresh child reports a parent ResultId without a corresponding parent
event, the client can retrieve that exact ancestor using read-only `GetResultById`
within the operation's existing evidence deadline. Retrieved ancestors provide
ownership context only. They do not count as fresh operations, terminal events,
or event-delivery compliance evidence. Tool and selected-process identity checks
still apply, and missing or conflicting ancestry remains unproven.

`GetResultById` must return the exact requested ResultId, not a parent or another
related result. Where an OPC UA adapter uses a separate controller API, verify
firmware/API compatibility before changing test expectations; a successful adapter
build or a newer firmware date alone does not establish that compatibility.

Measurement-content checks resolve reference-only child envelopes using their exact
ResultIds and read-only `GetResultById` on the method client. The original event
envelopes are unchanged: retrieved content cannot prove self-contained packaging,
event delivery, a fresh operation or process completion. Unavailable child content
is reported as inconclusive; missing FINAL values in available measurement content
remain assertion failures.

Counter reporting distinguishes an absent InterventionResult from a complete
InterventionResult whose Tool/process attribution cannot be proven
(`counter_result_context_mismatch`). Both leave the counter experiment inconclusive
without retrying the mutation. The latter must be investigated using the reported
AssociatedEntities and parent links, not treated as an event timeout.

The guarded workflows track unfinished or unknown Tool/process state in memory
within the current run. A physical Tool's ProductInstanceUri, not an endpoint
spelling, keys this run's ownership and uncertainty checks. Concurrent tasks
inside a run share the same Tool ownership boundary.
Ownership covers the active workflow, not the remaining lifetime of its asyncio
task. Nested operations retain the lease until the root workflow exits.
Adapter-local mutable state is also leased before entry, so a competing task
cannot reset the active start budget or overwrite its acquisition state.
Releasing a workflow lease never clears uncertainty within the run.
An unresolved action blocks joining, counter, identifier and asset workflows
before further mutation in that run. This must not be interpreted as universal lifecycle
coverage of custom adapters or external callers. Capturing a
Batch result from a selected Job does not establish that the Job finished.
Failed counter attempts preserve their original disposition and reason for later
consumers rather than replacing them with independent retry errors.

There is no implicit reset, abort, compensating mutation or budget increase.
Controller availability and physical readiness for a deliberately started new run
are the operator's responsibility. The client does not infer current controller
state from an old timeout, read or write `.process-state` records, or require a
reconciliation command. Existing files and prior run reports remain historical
evidence and are not changed or used to block a new run.
Optional automatic preparation never authorizes recovery of an unresolved action.
Identifier cleanup is selective and attempted once, not retried on an uncertain
response. Verified absence does not settle a send whose delayed effect is unknown.
Asset restoration likewise cannot erase uncertainty about an unsettled first call.

A reset experiment must both prove restart at step one and settle its restarted
parent before reporting successful workflow completion. Step-one evidence alone
is insufficient. Completion uses normal already-approved starts, not hidden
reset/abort cleanup. If the unchanged ceiling or attribution is insufficient,
the workflow remains inconclusive and its unresolved state is preserved.
Definite rejections preserve any preceding accepted-start uncertainty. An
observed requirement violation remains FAILED independently of parent settlement.

Content evidence reuse also requires observed ServerArray identity, Server StartTime,
software/build identity and namespace mapping, alongside the current catalogue and
configuration key. Missing incarnation metadata disables reuse with a diagnostic.
A fresh action experiment must not substitute old content evidence. GetLatestResult
may return an owned parent or a reference-related child after compound execution,
but an unrelated later result cannot validate that experiment.

The simulator counter route invokes the actual IncrementJoiningProcessCounter
method against its explicitly seeded Batch fixture. It requires the correlated
INCREMENTED intervention, a referencing Batch update and the expected counter
change. A SimulateResults call, method presence or call acceptance alone cannot
replace that behavioral proof.
The simulator adapter checks the resolved route and the selected manifest's
method permissions. Fixture setup requires both SetJoiningProcessCounter and
SetJoiningProcessSize before its first mutation. The actual increment separately
requires IncrementJoiningProcessCounter. Simulator identity or a claimed CU does
not override a denied method, and generic specification tests cannot grant
themselves target-method authorization.

For status-sensitive counter checks, the status-preserving method helper is
available instead of Node.call_method. It retains the method StatusCode, input-argument statuses
and business output arguments even for Uncertain or Bad method responses.
Service success is recorded only after asyncua's session Call verifies the
response header. Lookup failures do not count as dispatched method calls.
An uncertain response or nonzero business status alone does not prove that no
mutation occurred, and does not authorize a retry.

### Evidence-provider contract

`helpers/evidence_provider_contract.py` defines the versioned, family-neutral
provider boundary. Specification assessors request exact obligations and evidence,
not a particular Program, Job or fixture. Providers return observations and
diagnostics, never a compliance verdict.

The default uses available evidence or approved execution of existing
configuration. Missing suitable evidence leaves the claimed obligation INCOMPLETE.
Catalogue classification and provider availability do not prove SUT support.
Content reuse cannot substitute for a bound fresh-observation or before/after
experiment. Returned evidence must match its SUT, target, run and acquisition scope.

Temporary fixtures require separate explicit approval, all required method and
workflow permissions, implemented lifecycle support, verified exclusive test
ownership and a non-overwriting creation guarantee. A prefix or an absent-before
check alone is insufficient. Production recipes and configuration are never
overwritten. Prior runtime bindings must be restored where they were changed.

The lifecycle is plan and admit, reserve ownership, prepare, verify ownership,
acquire evidence, then perform mandatory teardown in finalization. Teardown also
applies after interrupted or partially failed preparation, even when no ownership
receipt was returned. The durable scope journal reserves overlapping resources
atomically before mutation and preserves unresolved state across provider/run
recreation. Run identity is ownership, not the key used to hide older uncertainty.

Cleanup must verify all reserved resources absent, prior runtime state restored
and any uncertain actions reconciled. A failed, indeterminate, foreign or
incomplete cleanup receipt cannot release the scope or permit another mutation.
Preparation and cleanup are not implicitly retried. Original failure diagnostics
remain available alongside later rejection reasons.

Existing adapters require an explicit bridge to this contract. The contract does
not author vendor recipes, enable fixtures, change existing permissions or assert
that a provider implementation exists. Each implementation must demonstrate its
SUT capability, ownership and restoration guarantees before admission.

Discovery never rewrites the manifest, claims or approvals. A manifest changed
while the specification suite runs blocks subsequent workflows. Normal repeats
do not need `refresh-profile`; refresh is for deliberately pinned restrictions.

**Qualification:** PASS requires passing evidence for every claimed CU.
Blocked, partial, untested or inconclusive required coverage gives INCOMPLETE
(exit code 6), never PASS. Independent tests can continue after a restricted
workflow is blocked. Genuine configuration, connectivity and discovery failures
still stop the run. Pytest's raw skip transport does not determine qualification.
The outer runner preserves exit 6 as INCOMPLETE instead of collapsing it into
FAIL. JSON, human summaries and the target Excel cover separate execution health,
requirement qualification and selected claimed-scope completeness.

A completed parent result and complete child evidence are distinct. If a
terminal parent was captured but referenced children are missing, the workflow
diagnostic lists those ResultIds rather than claiming that no completed result
arrived. This remains incomplete evidence, not proof of a server defect or a
reason to issue additional starts. An accepted-start timeout does not establish
that manual operator action was required.

Exact workbook assessment is piloted for Increment Joining Process Counter and
Intervention Result. All applicable cases must pass, including the counter's
negative cases. Equivalent evidence is accepted only for the same mapped case
and its executed route. Missing mappings or unimplemented negative evidence
remain incomplete. Other CUs retain their existing CU-level assessment and must
not be described as fully mapped normative proof.

In explicit scope, new catalogue CUs missing from the table are **unreviewed**,
not unsupported. Previously approved tests can continue, but tests requiring
those new CUs stay disabled. JSON, text, Markdown and Excel identify the review
gap, and qualification against the newer catalogue remains **INCOMPLETE / 6**.
Neither formatting nor table completion guesses a support declaration.

The generated remote-start example is for regression on a dedicated test
controller. It includes stored-result and identifier method permissions and
asset-disable approval. Review all of these before using the example with a
real installation. They are not vendor capability claims or permission to
operate a controller. The universal template retains conservative defaults.
Private Tool identities, result windows and other risk settings must not be
copied merely to remove differences.

Claimed CUs outside the selected workflow scope remain visible and keep the
qualification INCOMPLETE. Do not change a true support claim to unsupported
merely to obtain PASS. Review the intended scope, enable a safe approved
workflow, or retain the explicit qualification gap.
Classification-only or skipped specification suites return **6 / Not tested**,
not zero. CI and wrappers must distinguish execution success from qualification
and propagate this nonzero exit. Excel uses a yellow Inconclusive cover and
sheet warnings for incomplete/not-tested runs, never a green Passed cover.

Candidate and action budgets bound physical work, not proof requirements.
`all_compatible` refers to the admitted candidate window, bounded by
`max_candidates`, not every program installed on the controller.
The overall select/start deadline covers that candidate window, including
per-candidate setup and final observation, with starts budgeted up to the smaller
of `max_total_start_invocations` and `max_candidates * max_start_invocations`.
This timing allowance does not increase either start ceiling or permit retries.
An issued start without its required evidence ends candidate progression.
Rejected or unattempted admitted candidates keep `all_compatible` incomplete.
New runner invocations can act again and do not restore previous controller
state. Exclusive controller ownership remains an operator prerequisite.
Normal select/start workflows recheck the original catalog and selected
identity before selection and again before each start. This reduces stale-target
races but does not make OPC UA calls atomic. The action journal's
`candidate_scope` record reports total catalog size, admitted candidate count
and configured cap, not a claim that every installed process was qualified.

Use the canonical runner for preflight, approvals and run-scoped evidence.
At pytest startup, the selected manifest's actual bytes are checked against the
runner's supplied hash. Direct pytest captures its own startup hash when none
was supplied, it does not replace an existing hash or grant workflow approval.
The session retains the selected path and hash, checks them before each test
and direct OPC UA method call, and checks the file before physical selection
and known state-changing helper calls. A detected edit or unreadable file is
BLOCKED evidence, not a qualification PASS. A session-created hash is released
at shutdown without deleting a different caller's hash.

These checks reduce mid-run changes. File reads and OPC UA calls are not atomic,
and no profile file is a controller lock. Direct pytest still needs the intended
runtime profile and explicit physical-action approvals.

[Shared versus installation-specific settings](../target_server_cu_profiles/README.md#keep-portable-and-local-profiles-aligned)
explains local maintenance without duplicated defaults or permission copying.

When creating a manifest or reviewing stale exact targets, use read-only discovery
to inspect Tool identities and current processes. Live discovery is not required
for an offline documentation edit or a reviewed change unrelated to target IDs:

```bash
python run_all_tests.py init-profile --endpoint opc.tcp://<controller-host>:40451 --output target_server_cu_profiles/controller.local.sut.yaml
```

### Refresh stale IDs without rebuilding the manifest

Discovery already fetches `GetJoiningProcessList` dynamically. An exact selector
still must match that catalog; runtime discovery never silently relaxes it.
After controller programs/sequences are recreated, use:

```powershell
python run_all_tests.py refresh-profile --profile .\target_server_cu_profiles\controller.local.sut.yaml
```

This reuses the prepared environment, the manifest's endpoint, and its declared
security/authentication. It does not install dependencies, clean run evidence,
override the endpoint, or change the controller's state. A configured Tool
ProductInstanceUri selects that exact Tool, including a non-first Tool in the
server's Tools folder. Missing or duplicate requested Tool identities stop
before catalog access; an empty configured PIU still requires a discovered Tool.

The guide lists current process IDs, origins, selection names and process
classifications. For each group of related exact references, explicitly choose
a process number, enter `k` to keep fully current, strategy-valid unique matches,
or `q` to cancel. A unique primary match alone does not permit keeping stale
secondary identifiers.
There is no default process choice. Matching Job, counter-effect and intervention
parent references are reviewed together; unrelated references are reviewed
separately. Process classification alone is not proof of result capability.
Same process IDs remain grouped even when secondary metadata needs refreshing.
Conflicting secondary-only identities stay separate; ambiguous/transitive
secondary-only bridges require manual review instead of merging unrelated roles.
Without a process ID on either reference, both active `match_by` keys must be
present and equal in the shared identity. A shared origin alone cannot absorb
an unrelated name-matched reference. ID-anchored Job/counter groups can still
include their origin-only intervention parent.
The catalog displays all advertised `SelectionNames`, sorted. An explicit
advertised alias is preserved; a sole associated name is resolved even without
a scalar display name. Multiple names require an explicit advertised alias
whenever the selector uses or stores `selection_name`, not just for
`selection_name_only`. Unused aliases do not block an identifier-only refresh.
`selection_name_only` also requires a unique advertised wire name;
`all_available` requires all three identifiers. The selected strategy is never
silently weakened.

Review the diff, then type `REFRESH <profile filename>` exactly. All changes are
saved together by one local file replacement, only after manifest validation
and unique live-selector checks. The original comments, newline style,
exact-match policies, `match_by`, identifier strategies, CU claims, risk approvals
and counter limits are preserved. Missing required identifier fields are added;
IDs are not copied into tracked templates automatically.

Cancellation, EOF, ambiguous identities, missing required identifiers, discovery
failure or a detected profile edit during review stops without saving. YAML
anchors/aliases, duplicate/merge keys and block-scalar identifiers require manual
review instead of an unsafe rewrite. Non-interactive refresh is rejected before
connecting. This is a snapshot-based repair, not a controller reservation or
whole-run lock; run `--preflight-only` afterward and approve workloads separately.

### When setup blocks a run

The terminal and text/Markdown summaries name the actual manifest, effective
endpoint and public field to review, such as
`workflows.process_selectors_by_classification.job.joining_process_id`.
Stale-selector failures include a reviewed-refresh command; discovery or
security failures require restoring catalog access first, not replacing IDs.
The recheck command is preflight-only and retains the effective endpoint.
Before refreshing, confirm the saved endpoint matches that controller:
`refresh-profile` deliberately uses the saved manifest, not runtime overrides.
Keep exact-match policies, claims, security and risk approvals unchanged.

---

## 3) SUT Manifests & Setup Recipes

### Available SUT manifest catalog:
- **Universal template:** `target_server_cu_profiles/template.sut.yaml`
- **Checked-in simulator:** `target_server_cu_profiles/simulator.sut.yaml`
- **Remote-start multi-operation workflow:** `target_server_cu_profiles/controller_remote_start.sut.yaml`
- **Manual trigger workflow:** `target_server_cu_profiles/controller_manual_trigger.sut.yaml`

One System Under Test is described by exactly one `*.sut.yaml` manifest. Every field is documented in the generated [SUT Manifest Field Reference](SUT_MANIFEST_REFERENCE.md).

### Prepare a real controller manifest

If the controller matches the supplied claim baseline, use the committed generic example directly and pass installation values at runtime:

**Windows (PowerShell):**
```powershell
python run_all_tests.py `
  --profile target_server_cu_profiles/controller_remote_start.sut.yaml `
  --endpoint opc.tcp://<controller-host>:40451 `
  --joining-process-id <joining-process-id> `
  --joining-process-origin-id <joining-process-origin-id> `
  --preflight-only
```

**Linux / macOS (Bash / Zsh):**
```bash
python run_all_tests.py \
  --profile target_server_cu_profiles/controller_remote_start.sut.yaml \
  --endpoint opc.tcp://<controller-host>:40451 \
  --joining-process-id <joining-process-id> \
  --joining-process-origin-id <joining-process-origin-id> \
  --preflight-only
```

Optional runtime overrides are also available through environment variables:
`OPCUA_SERVER_URL`, `OPCUA_TOOL_PRODUCT_INSTANCE_URI`, `OPCUA_JOINING_PROCESS_ID`, `OPCUA_JOINING_PROCESS_ORIGIN_ID`, and `OPCUA_CAPABILITIES_FILE` (which now names a `*.sut.yaml` manifest).

When an exact process selector is configured, `--preflight-only` also reads
`GetJoiningProcessList` and requires exactly one live match. This check is
read-only: it does not select a process or invoke a joining method.

### Creating a local manifest

Create a local manifest when the controller's workflow or claimed CUs differ from the committed example. Copy one file - there is no companion file to keep in sync:

**Windows (PowerShell):**
```powershell
Copy-Item target_server_cu_profiles/template.sut.yaml `
  target_server_cu_profiles/controller.local.sut.yaml
```

**Linux / macOS (Bash / Zsh):**
```bash
cp target_server_cu_profiles/template.sut.yaml \
   target_server_cu_profiles/controller.local.sut.yaml
```

Then review and update `controller.local.sut.yaml`; local copies remain ignored:

| Setting | What to enter |
|---|---|
| `lifecycle.mode` | `external` for a real controller; `auto_simulator` only for the checked-in simulator |
| `connection.endpoint` | Real `opc.tcp://host:port` endpoint |
| `connection.security_mode` / `connection.security_policy` | Session security; certificate paths sit alongside them |
| `authentication.source` | `anonymous`, `prompt`, `file`, or `environment` - references only, never a secret value |
| `capability_claims.active_profile` / `supported_facets` / `cu_overrides` | The controller's authoritative CU claims |
| `workflows.tool_selector.policy` | `first_ready` (default) picks the first Connected & Enabled Tool; `first_available` picks the first Tool with a URI; `discover_unique` requires a single Tool; `exact_match` requires `product_instance_uri` |
| `workflows.tool_selector.product_instance_uri` | Optional Tool PIU override (required when `policy: exact_match`); leave empty for policy-driven discovery |
| `workflows.process_selector.policy` | `first_compatible` is the schema default; committed presets may use `first_ready`. Non-exact policies order direct Classification matches first, then bounded Job candidates for Batch or Sync evidence. `all_compatible` tests every ordered candidate; the other policies stop after the first proof. A result-specific `exact_match` may intentionally cross process Classification, but the requested completed result is always the capability proof. |
| `workflows.process_selector.joining_process_id` | Advertised Process ID used for exact matching by default; no automatic identifier fallback |
| `workflows.process_selector.joining_process_origin_id` | Advertised origin ID used when explicitly selected by `match_by` or included by `identifier_strategy` |
| `workflows.process_selector.selection_name` | Advertised SelectionName used only by an explicitly configured matching or payload strategy |
| `workflows.process_selectors_by_classification.<classification>` | Optional per-classification selectors (`single`, `job`, `batch`, `sync`) |
| `workflows.max_start_invocations` | Per-process StartSelectedJoining safety ceiling, not the expected process size (default: 6). An uncertain or rejected start is not permission to retry. |
| `workflows.max_candidates` | Maximum admitted process candidates per workflow (default: 3) |
| `workflows.max_total_start_invocations` | Total attempted starts across the admitted candidates, including failed or uncertain calls (default: 6) |
| `workflows.max_start_invocations_by_result_classification` | Additional ceilings for the selected parent's result classification, bounded by the per-process and total ceilings |
| `workflows.consecutive_start_delay_seconds` | Settlement delay after selection before workflow actuation, and pacing between consecutive starts (default: 0.25s) |
| `workflows.process_selector.identifier_strategy` | Strategy for populating JoiningProcessIdentificationDataType (`id_only` by default, `id_with_origin`, `id_with_selection_name`, `all_available`, `selection_name_only`) |
| `workflows.expected_results.classification` | Final result layer, such as `single`, `batch`, or `job` |
| `workflows.expected_results.intermediate_classifications` | Earlier layers, such as `[single, batch, intervention]` |
| `triggers.result.mode` | `start_selected_joining`, `manual_trigger`, `observe_only`, or `none` |
| `timeouts.*` | Separate budgets for passive observation, active results, whole workflow, operator action, and single method calls |
| `scoring.mode` | `strict_profile` (strict claimed scope, default), `diagnostic`, or `acceptance` |

Specification-test client fixtures use a 30-second connection-health probe interval
and deadline, independently of the 120-second request timeout. This avoids asyncua's
default one-second health probe disconnecting a busy controller during datatype
loading or other traffic. A failed probe still disconnects the client; joining
commands are not automatically reconnected or retried.

Profile and endpoint runs reject forwarded pytest arguments after `--`, rather
than silently ignoring selectors and running the full specification suite.
Use direct pytest with the target runtime environment for targeted diagnostics.
Discovery preserves transport, session and timeout errors instead of reporting
missing nodes. A failed GetLatestResult call or absent result after a successful
trigger is reported as a retrieval failure, not a missing SequenceNumber.

An `external` manifest that still contains `<placeholder>` values in an *operational* field
fails fast before any server is contacted. Descriptive prose (`name`, `description`) is not
scanned, so an example may keep documenting the word `<placeholder>` and still be live-ready
once its real values are filled in.

### Connection security and credentials

`connection.security_mode` / `connection.security_policy` and `authentication.source` are
applied end to end: preflight, `inspect`, `init-profile`, and every asyncua client the pytest
fixtures open use the same declaration. A declared setting that cannot be applied is a
blocking `connection_security` preflight check — it is never ignored and never downgraded
to an anonymous, unsecured session.

| `authentication.source` | Where the credentials come from | Notes |
|---|---|---|
| `anonymous` | No user identity | Default, and what the checked-in simulator uses |
| `prompt` | Operator, at run time | Only with `--interactive-prompts`; an unattended run fails preflight instead of blocking on stdin |
| `file` | A local, git-ignored YAML/JSON file with `username` / `password` | `authentication.credentials_file` holds the path; relative paths resolve against the manifest |
| `environment` | Environment / CI secret variables | `authentication.username_env_var` and `authentication.password_env_var` hold variable *names*; an unset variable fails preflight |

A secure channel (`security_mode` other than `None`) requires
`connection.client_certificate_path` and `connection.client_private_key_path`;
`connection.server_certificate_path` pins the server certificate and
`connection.trust_store_path` installs a trusted-issuer/CRL validator. The manifest never
holds a secret value, and no credential is ever written to a log, report, or error message.

---

## 4) Run Commands

- **Read-only preflight check:**
  ```bash
  python run_all_tests.py --preflight-only --profile target_server_cu_profiles/controller.local.sut.yaml
  ```
- **Classification without invoking specification tests:**
  ```bash
  python run_all_tests.py --profile target_server_cu_profiles/controller.local.sut.yaml --skip-spec-tests
  ```
- **Full validation (Phase 1 + preflight + specs + evidence):**
  ```bash
  python run_all_tests.py run --profile target_server_cu_profiles/controller.local.sut.yaml --endpoint opc.tcp://<host>:40451
  ```
- **Preflight + specs + evidence only (skipping Phase 1):**
  ```bash
  python run_all_tests.py run --phase2 --profile target_server_cu_profiles/controller.local.sut.yaml --endpoint opc.tcp://<host>:40451
  ```
- **Guided / manual run with interactive prompts:**
  ```bash
  python run_all_tests.py --phase2 --profile target_server_cu_profiles/controller.local.sut.yaml --mode guided --interactive-prompts --output-dir test-results/target-server-cu/controller-guided
  ```

### Focused direct-pytest diagnostics

Prefer the runner for qualification. For a focused developer test, use a separate
PowerShell session and the already prepared client environment. Set both the
target runtime profile and the CU manifest, plus the intended endpoint:

```powershell
$profile = (Resolve-Path .\target_server_cu_profiles\controller.local.sut.yaml).Path
$env:OPCUA_TARGET_SERVER_PROFILE = $profile
$env:OPCUA_CAPABILITIES_FILE = $profile
$env:OPCUA_SERVER_URL = 'opc.tcp://<host>:40451'
.\.venv_test\Scripts\python.exe -B -m pytest .\specification_tests\test_joining_process.py -x -v --tb=short -rs
```

These are live tests and may execute approved physical workflows. Establish
exclusive controller ownership and review the manifest's permissions first.
`OPCUA_CAPABILITIES_FILE` alone controls CU claims; it does not activate the
target workflow adapters. The canonical runner configures these variables
automatically. Focused runs may correctly return INCOMPLETE / exit 6 because
they do not execute the full claimed scope.

---

## 5) Output Artifacts

Every Target Server run generates structured evidence artifacts in the output directory (default: `test-results/target-server-cu/`):

- `target-server-cu-report.json` — machine-readable JSON evidence report with check details
- `target-server-cu-summary.txt` — human-readable ASCII summary for console inspection, including unique live test totals and per-CU test counts
- `target-server-cu-summary.md` — GitHub-compatible Markdown summary table with a `Test Counts` section (unique totals plus a collapsed per-CU table). Per-CU rows overlap for multi-CU tests and must not be summed; see [test-results.md](test-results.md#test-counts-runner-steps-vs-live-tests-vs-cus)
- `spec-tests.xml` — standard JUnit XML report for CI/CD integration
- `cu-coverage-report.json` — run-scoped 123-CU classification report
- `report-controller.xlsx` — automatically generated Excel traceability workbook, written inside the run's own output directory. It is copied elsewhere only when `--excel-out FILE` is explicitly passed. If the run completed but this workbook cannot be produced — for example because `spec-tests.xml` or `cu-coverage-report.json` is missing — the target run fails; only `--excel=never` and `--excel=on-success` decline it benignly.

---

## 6) Domain Semantics, Process Selection, and Safety Rules

### Generic JoiningProcess abstraction
The IJT information model uses `JoiningProcess` as the generic process abstraction. A controller can use it for a program, batch, job, sequence, application recipe, or another technology-specific process. Shared test client logic never encodes vendor-specific vocabulary.

### Process Selection
Exact matching uses one explicit criterion, configured by `match_by`:
`joining_process_id` (the default), `joining_process_origin_id`, or
`selection_name`. The selected field must have a value, and exactly one
advertised process must match. The runner never falls back to another field
when the configured value is stale or absent. `identifier_strategy` is separate:
it controls which identifiers are sent in the `SelectJoiningProcess` payload
after a process has been matched.

`identifier_strategy: selection_name_only` is an explicit compatibility option:
send only the selected process's advertised SelectionName, with empty
JoiningProcessId and JoiningProcessOriginId. No vendor-specific token is constructed.
An explicit `selection_name` must be advertised by that process; otherwise exactly
one advertised name is required. Before selection, a fresh process-list read must
confirm that the name identifies exactly one process. Missing or ambiguous names
block execution. The portable default remains `id_only`; there is no automatic
retry with another payload strategy.

For ordinary result testing, use `first_compatible` when the operator has approved
any compatible advertised process for execution. Candidates follow server-returned
order and commands use their current IDs with `id_only`. Availability and
classification are not physical safety checks: preparing the tool/controller and
approving the candidate recipes are operator prerequisites. Use `exact_match`
with a reviewed ID to restrict testing to a specific process. Counter mutations
separately require an explicit counter-effect scenario with either `exact_match`
or an approved `discover_unique` policy resolving exactly one current process.

For workflows testing both single tightening programs (for SingleResult) and multi-operation Jobs/Batches:
```yaml
workflows:
  process_selectors_by_classification:
    single:
      policy: exact_match
      match_by: joining_process_id
      joining_process_id: "<program-id>"
    job:
      policy: exact_match
      match_by: joining_process_id
      joining_process_id: "<job-id>"
    batch:
      policy: first_compatible
```
`first_compatible` prefers direct standard-classification matches and may then try a
bounded Job candidate for Batch or Sync evidence. `all_compatible` is an explicit
opt-in that tests the admitted candidate window within the per-process and total
start limits; it does not mean every installed process.

### Result layering & multi-operation starts
Joining-process and result classifications are different OPC 40450-1 domains:

- `JoiningProcessMetaData.Classification`: Other=1, Program=2, Sync=3, Batch=4, Job=5.
- `ResultMetaData.Classification`: Single=1, Sync=2, Batch=3, Job=4, Stitching=5, Intervention=6, Text=7.

Runtime selection and `init-profile` use the joining-process domain. Never copy a
numeric value from one domain into the other. Discovery treats advertised process
metadata as authoritative; name-based suggestions are advisory only when that
metadata is absent or unusable and must be reviewed before use.

YAML keys such as `single:`, `sync:`, `batch:`, and `job:` are human-readable
configuration labels only. They are converted at the configuration boundary;
execution and OPC UA comparisons use the integer result constants and the distinct
joining-process classification enum. These strings are never sent as OPC UA
Classification values.

The requested-result event test subscribes on the Server object to
`RequestedResultEventType` before calling `RequestResults`. It requires an actual
event whose `Result` payload carries a ResultId and SequenceNumber in
`ResultMetaData`; a variable update alone cannot pass this event-access test. When
the server also exposes the `Result/ResultMetaData/ResultId` and `.../SequenceNumber`
sub-variable event fields, they must equal the payload values. Sequence-filtered
responses must fall
within the requested range. When testing against the simulator (`is_simulator=True`),
the simulator replays results with synthetic ResultIds within the requested sequence
window. On a Controller, strict ResultId correlation is mandatory: production results
must be replayed with their freshly captured ResultId; simulated results (`IsSimulated=true`)
may use a synthetic ResultId or skip if the controller only replays non-simulated stored
results. Variable-access
tests remain separate. This does not change configured ranges or busy retries,
and does not prove controller retention or restart recovery.

Result classification describes the evidence emitted by the workflow, not the vendor name of the process:
- For a compound process that produces multiple result layers (Job, Batch, or Sync), configure `workflows.max_start_invocations` (default: 6) and `workflows.consecutive_start_delay_seconds` (default: 0.25s).
- An exact result-specific selector may authorize a cross-classification candidate, but metadata never proves result capability. Success requires a correlated completed result with the requested result classification.
- The reusable trigger subscribes before starting, selects the generic `JoiningProcess`, waits for a completed Tool-correlated `SingleResult` as operation evidence, and applies the pacing delay between starts.
- The trigger exits on any matching non-partial terminal `SyncResult`, `BatchResult`, or `JobResult` (COMPLETED, ABORTED, or FAILED), then qualifies the configured expected state. An unexpected state cannot prompt another start or pass as successful evidence.
- Queue inspection and the pacing drain reduce extra-start races, but cannot eliminate the small check-to-start window without an atomic controller readiness/completion signal.
- The runner preserves CUs for the primary `classification` and every declared item in `intermediate_classifications` (e.g. `classification: job` with `intermediate_classifications: [single, batch, intervention]`).
- With `workflows.evidence_reuse.enabled: true`, complete lossless progression evidence is immutable and reusable only while endpoint, Tool PIU, current process-list fingerprint, selected process, policy, start bound, and pacing still match. Event-causation and state-mutation workflows never use this cache.
- OPC 40450-1 defines an optional Self-Contained Consolidated Result CU. The simulator exercises inline and reference packaging; other servers may claim either supported form.
- Reference-mode combined results identify separately transferred children through metadata stubs. The Test Client validates the declared packaging, never infers it from the server being a controller or simulator, never trusts arrival order, and closes references by ResultId.

`consecutive_start_delay_seconds` is not a global delay between OPC UA requests.
Normal browse/read calls are not paced by it; correlated-result and completion
waits can add further runtime. A paced qualification run is not a burst-load or
concurrency stress test.

### Transactional physical workflows

- Identifier workflows generate one run-unique value, verify it through `GetIdentifiers`, and attempt selective cleanup once in `finally`, followed by absence verification. Cleanup is not implicitly retried. `ResetAll` requires its own explicit risk and workflow approvals; an identifier round trip alone does not authorize it.
- Counter-effect scenarios are explicit entries under `execution_policy.counter_effects`. Use `process_policy: exact_match` for a reviewed specific target, or explicitly opt into `discover_unique` for exactly one current process of the configured standard classification. Ambiguous targets and implicit fallbacks are rejected. Preflight checks uniqueness, and runtime checks the bound identity again before mutation. A completed `InterventionResult` must be attributable to the selected Tool and process, directly or through the verified VirtualStation/parent relationships described above. When an affected classification is configured, one loss-aware subscription must also observe a matching partial or final affected-result update that explicitly references that InterventionResult. The counter action does not prove that the parent reached its final boundary.
- `triggers.event.mode: workflow_actions` maps an event CU to an approved physical cause. Select-process events prefer a Program different from the active one; an authorized deselection may be needed when only the active candidate is available. These actions do not start joining. Asset-enable-state event workflows deliberately finish with verified `EnableAsset(true)`; this differs from the generic asset-toggle test, which restores the original observed state.
- Identifier events and Conditions should remain unclaimed when the controller firmware provides no safe deterministic cause.

### Autonomous Abort and Reset Workflows
The Test Client provides dedicated trigger methods for compound multi-step sequence abort and reset testing:
- **Required permissions**: Authorize `SelectJoiningProcess`, `StartSelectedJoining`, and the tested `AbortJoiningProcess` and/or `ResetJoiningProcess` method. Existing start ceilings still apply.
- **Approved workflows**: Add `remote_abort_job` and/or `remote_reset_job` to `workflows.approved`.
- **Abort workflow (`trigger_abort_job`)**:
  - Selects a multi-step Job (Classification 5) or Batch (Classification 4).
  - Starts step 1 via `StartSelectedJoining` and waits for its completed intermediate `SingleResult` to confirm active sequence state, strictly ensuring the parent sequence did not finish prematurely.
  - Invokes `AbortJoiningProcess(ToolPIU, Identification, LocalizedText(Message))` with `target_server_authorized=True`.
  - Asserts that the terminal consolidated result arrives with `IsPartial=False` and `ResultState` in `workflows.expected_results.expected_abort_result_states` (default `[3]` = `ABORTED`), correlating via `TOOL` or `VIRTUAL_STATION` + process identity and validating `associated_entities` under `context: counter_intervention`. Use `[3, 4]` only when the reviewed controller contract accepts both `ABORTED (3)` and `FAILED (4)` after abort; do not broaden expectations merely to turn a failure green. Set `workflows.expected_results.reject_ok_evaluation_on_abort: true` only when the server contract requires rejection of an aborted result evaluated as `OK (1)`.
- **Reset workflow (`trigger_reset_job`)**:
  - Requires a live subscription client to establish and verify sequence state.
  - Starts step 1 and verifies the intermediate `SingleResult`.
  - Invokes `ResetJoiningProcess(ToolPIU, Identification)` with `target_server_authorized=True`.
  - Drains queued notifications, issues `StartSelectedJoining` again, and requires a new `ResultId`, increasing `SequenceNumber`, and matching non-empty `StepId`. This rejects stale notifications and proves return to the same first step.
  - Reports the conformance probe as inconclusive and skips it when `StepId` is absent because OPC 40001-101 makes this field optional; observing another `SingleResult` alone cannot prove which step ran.
  - Continues normal owned joining within the remaining approved start ceilings until the restarted parent is terminal. First-step proof alone does not settle the process or complete the workflow.
- **Dedicated Trigger Routing**: The Abort event and Reset functional conformance tests call the dedicated trigger methods. Unsupported adapters return a non-triggering outcome, while approved `start_selected_joining` profiles run the autonomous workflows. `trigger_job()` remains dedicated to normal Job execution under the configured expected terminal state, not a substitute for Abort or Reset.

### State-change safety & permissions
- Adding a method to `state_changing_methods.allowed_methods` is a **safety permission only** — it does not enable CUs or create tests. The manifest's `capability_claims` determine which CUs are enabled.
- State-changing specification probes are blocked on real targets. Only configured workflow adapters may invoke them.
- `EnableAsset(false)` requires explicit argument-level opt-in. The generic state-restoration test restores the original observed Enabled value; the event workflow deliberately restores and verifies `true`. Neither restoration path clears an unresolved earlier action.
- For `EnableAsset(true)`, use `when_disabled` to monitor `Tool.Parameters.Enabled`, or `always` when harmless reassertion is needed for a controller's remote-readiness state.
- Use the discovered Tool `ProductInstanceUri` for Tool-context operations (identifications, joining processes, counters, interventions). Do not use the Controller PIU for Tool methods.
- Keep real endpoints, ProductInstanceUris, process identifiers, serial numbers, and reports containing private details in ignored local files.
