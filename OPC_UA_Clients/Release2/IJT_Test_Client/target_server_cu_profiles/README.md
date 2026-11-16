# SUT Manifests

This directory holds **SUT manifests** (`*.sut.yaml`) for validating OPC UA Industrial Joining Technologies (IJT) systems under test (SUT) against OPC 40450-1 (Release 2.0).

One System Under Test is described by exactly **one** manifest. The previous paired `*.profile.yaml` + `*.capabilities.yaml` model has been replaced: connection, authentication references, authoritative Conformance Unit (CU) claims, approved workflows, trigger modes, execution/risk policy, timeout budgets, scoring strictness, and reporting/redaction now live in a single versioned file.

- Field-by-field reference: **[SUT Manifest Field Reference](../docs/SUT_MANIFEST_REFERENCE.md)** (generated)
- Server integration, process selection, layered results, and safety rules: **[Target Server CU Guide](../docs/TARGET_SERVER_CU_GUIDE.md)**

---

## Manifest catalog

All committed manifests are generated from the schema metadata and built-in presets in `helpers/sut_manifest.py`.

| File | Purpose |
|---|---|
| [`template.sut.yaml`](template.sut.yaml) | Fully commented universal template with safe defaults and `<placeholders>` |
| [`simulator.sut.yaml`](simulator.sut.yaml) | Complete, placeholder-free manifest for the checked-in IJT simulator |
| [`controller_remote_start.sut.yaml`](controller_remote_start.sut.yaml) | Generic controller running a multi-operation job started remotely |
| [`controller_manual_trigger.sut.yaml`](controller_manual_trigger.sut.yaml) | Generic controller where an operator physically triggers the tool |

Regenerate them after any schema change:

```bash
python scripts/generate_sut_manifest_docs.py          # write template, examples, and field reference
python scripts/generate_sut_manifest_docs.py --check  # fail if a committed artifact drifted
```

The simulator preset explicitly permits counter setup (`SetJoiningProcessCounter`
and `SetJoiningProcessSize`) and the increment-effect check
(`IncrementJoiningProcessCounter`). These permissions support the specification
tests on the disposable simulator; they do not grant any controller permissions.

---

## Why there are two YAML directories

These are different schemas, not ten competing controller configurations:

| Directory | Files | Responsibility |
|---|---|---|
| `target_server_cu_profiles/` | Four committed SUT examples plus ignored local copies | One complete runtime manifest per SUT: connection, targets, CU claims, approved actions and evidence policy |
| `profiles/` | Four capability bundles plus `facets.yaml` | Reusable specification-to-CU definitions, with no endpoints, controller identities or physical-action approvals |

The four capability bundles are `basic_joining_system`, `general_joining_system`,
`asset_management` and `full_specification_coverage`.
With `capability_claims.cu_scope_policy: explicit`, only the `supported` and
`manual_required` rows in `cu_overrides` define claimed scope. The generated
examples list all 123 current CUs. The profile and facet names provide context,
they do not add claims beyond that table.

Older manifests default to `cu_scope_policy: inherit`. In that mode,
`active_profile` and `supported_facets` add CU groups before overrides apply.
Selecting full specification coverage in inherited mode claims all catalogue
CUs. A claim is never proof that a controller supports or passed them.

Do not pass a capability-definition file directly to `run --profile`, or place
controller connection/approval settings in `profiles/`. Use one SUT manifest.
Definition fields describe explicit specification metadata, not execution
defaults. Similar fields share comments within their own schema. Different
scenarios deliberately retain different values.

---

## Rules the loader enforces

| Rule | Effect |
|---|---|
| **No secrets** | A manifest may reference a local credentials file or environment variable *names*. Inline passwords, tokens, and keys are rejected. |
| **Claims are authoritative** | `capability_claims` defines the scored scope. Discovery observations never silently change it. |
| **Strict claimed scope** | `scoring.mode` defaults to `strict_profile` with `claimed_scope_only: true`. |
| **Placeholders fail fast** | An `external` lifecycle run stops before contacting a server while any operational field still holds a `<placeholder>`. Descriptive prose (`name`, `description`) is never scanned. |
| **Declared security is applied** | `connection.security_*` and `authentication.source` are applied to preflight, discovery, and every test session. A setting that cannot be applied blocks the run instead of falling back to an anonymous, unsecured session. |
| **No legacy paired files** | A `*.profile.yaml` or `*.capabilities.yaml` file produces a clear migration error. |

Keep manifests holding real endpoints, ProductInstanceUris, or process IDs outside the repository. Only `template.sut.yaml`, `simulator.sut.yaml`, `controller_remote_start.sut.yaml`, and `controller_manual_trigger.sut.yaml` are committed; every other `*.yaml` here is git-ignored.

---

## Quick start

The remote-start example explicitly approves bounded discovery and resolves
current process IDs on each run. No vendor-specific SelectionName is required.
The universal template keeps this approval disabled until a tester enables it.
See [automatic and exact selection](../docs/TARGET_SERVER_CU_GUIDE.md#repeat-runs-without-updating-process-ids).

### Keep portable and local profiles aligned

Use the generated remote-start example for common execution settings and a
single ignored local copy for installation details. The remote-start example
is a dedicated-test-controller regression baseline, with standard stored-result
and identifier method permissions and asset-disable approval. Review these
permissions for the installation before execution. The universal template
does not inherit this broader approval policy.
The current remote-start preset uses `first_ready` Tool
discovery (with automatic VirtualStation discovery from owned joining results),
bounded `first_ready` / `first_compatible` process discovery, `id_only`,
eight-start (`24` total) bounds, `1..10` stored-result range checks, Joint
CRUD round-trip with cleanup, final-result proof, strict cleanup policy and
current-run evidence reuse. Physical/fault-only CUs declared `manual_required`
are deferred under `manual_deferred_cus` during unattended `automated` runs
and verified during `guided` runs.
Strict cleanup does not imply controller restoration when cleanup actions are
disabled. The universal template still requires explicit discovery approval.

Keep differences that express real installation facts—often only
`connection.endpoint` (plus security/authentication or an optional explicit Tool
URI when pinning a non-first Tool). Never copy generic permissions into an owner
profile without review or downgrade claims just to obtain PASS. The example's
claims are a reference baseline, not a universal vendor capability baseline.
Final proof is mandatory in the remote-start example even where older versions
accepted an intermediate result.

The generic example declares `consolidated_result_with_references`,
`joint_management`, `joint_data`, `delete_joint`, and `engineering_units` as
supported. Review them before execution and mark a CU `unsupported` if a target
controller genuinely omits that capability. Missing permission or setup does not
make a supported feature unsupported; that remains a blocked test.

The generic scenario name is **Remote Start Multi-Operation Job**. A corresponding
local copy can retain that name and description. Controller identity belongs in connection and Tool
selection fields. Keep pending setup status in project notes or diagnostics,
not in the scenario name or YAML comments.

Fixed runtime fields show their purpose, options and schema default. Counter
scenarios are block mappings with field-level comments. CU rows stay short,
with status meanings and omission policy explained once above the table.
Defaults and the value chosen by a preset are different concepts.
For a readable local copy with the same field order and comments, without
replacing any values:

```powershell
python -B .\scripts\generate_sut_manifest_docs.py --format-local .\target_server_cu_profiles\controller.local.sut.yaml
```

Formatting removes only verified marked blocks and exact copies of known
schema explanations. Ambiguous/local notes survive. It orders mapping fields
without reserializing scalar values or reordering action lists. Values, scalar
formatting and newline style survive, and parsed values are checked before
saving. This is not YAML merging, runtime inheritance or permission alignment.

The older `--annotate-local` mode remains available for marked comment blocks
without field reordering. Both modes verify existing block hashes and exact END
markers, and refuse edited blocks rather than deleting owner notes. Unhashed
blocks are accepted only if canonical. In compact files, edited unmarked prose
is preserved rather than guessed to be disposable schema text.
An unclosed BEGIN or unmatched END marker also stops the refresh. Marker-like
text inside a YAML string remains data, not a schema comment.

Invalid/anchored/duplicate-key documents require manual review. Saving uses the
existing guarded atomic profile writer, detects intervening edits and never
contacts a controller. Keep editable owner notes outside BEGIN/END markers.
The generated-artifact check plus unit comment-consistency checks guard
documentation for the committed files. Local values remain owner-controlled.

### One source, regeneration and read-only checks

Common field guidance, defaults and presets belong in **helpers/sut_manifest.py**.
Do not edit generated comments independently. After changing that source,
regenerate all tracked examples and the reference together:

```powershell
python -B .\scripts\generate_sut_manifest_docs.py
python -B .\scripts\generate_sut_manifest_docs.py --check
python -B .\scripts\generate_sut_manifest_docs.py --check-local .\target_server_cu_profiles\controller.local.sut.yaml
```

Use an existing prepared client Python environment for these offline commands.
`--check` verifies tracked generated files without writing.
`--check-local` checks common field guidance in one selected ignored file,
without changing values or notes. Label installation-specific comments with
`# Local note:`. Stale, missing or duplicate shared guidance fails this quality
check, not an otherwise valid approved controller run.

`--format-local` refreshes common comments, field order, blank-line spacing
and mapping-list style using the generated layout.
`--annotate-local` adds verified marked comments without reordering.
`--complete-local-cus` converts an older inherited table to explicit scope
while preserving its current effective claims:

```powershell
python -B .\scripts\generate_sut_manifest_docs.py --complete-local-cus .\target_server_cu_profiles\controller.local.sut.yaml
```

For an already explicit table, missing new catalogue rows remain unreviewed.
Neither formatting nor completion guesses their support or adds them as
unsupported. Previously approved tests can continue, but tests requiring a new
CU stay disabled. Reports retain the approved results and identify unreviewed
CUs as untested. Qualification against the newer catalogue remains
**INCOMPLETE / exit 6** until their declarations are reviewed.

The local pre-commit hook and existing CI unit checks detect tracked drift.
Ignored local files require their separate read-only check. Making the CI job
a required merge check is a repository-admin decision, not a change made here.
No check can prevent a tool or administrator from deliberately bypassing it.

Use plain comments about what a setting controls. Keep run dates, previous
results and controller observations in project notes or reports. A past pass
does not prove current support or qualification. In explicit scope, a missing
CU row means unreviewed, not unsupported. In legacy inherited scope, a missing
override follows the selected profile and facets. Compare effective claims,
not just the number of entries.

The generic remote-start example uses `first_ready`, which selects a Connected
and Enabled Tool in deterministic order and prefers Tools advertising processes.
`discover_unique` is a different policy: it requires exactly one Tool Object
when no ProductInstanceUri is configured. An explicit ProductInstanceUri takes
precedence and must match exactly one Tool. Use that exact binding when only one
particular Tool is approved; readiness-based discovery is not permission to
operate every Tool. Tool discovery does not filter by `capability_tags`.
Process discovery remains available within that Tool scope.
See [Tool and process selection](../docs/TARGET_SERVER_CU_GUIDE.md#which-yaml-file-controls-what).

All commands run via `run_all_tests.py` from `OPC_UA_Clients/Release2/IJT_Test_Client`:

```bash
# 1. Read-only discovery (safe, no state changes):
python run_all_tests.py inspect --endpoint opc.tcp://<host>:40451

# 2. Auto-create a manifest from live discovery:
python run_all_tests.py init-profile --endpoint opc.tcp://<host>:40451 --output target_server_cu_profiles/controller.sut.yaml

# 3. Classification-only preflight (validates config & TCP; no live tests):
python run_all_tests.py run --profile target_server_cu_profiles/controller.sut.yaml --endpoint opc.tcp://<host>:40451 --preflight-only

# 4. Full validation run (Phase 1 quality + preflight + live specification tests + evidence):
python run_all_tests.py run --profile target_server_cu_profiles/controller.sut.yaml --endpoint opc.tcp://<host>:40451

# 5. Specification tests only (skips Phase 1 static analysis):
python run_all_tests.py run --phase2 --profile target_server_cu_profiles/controller.sut.yaml --endpoint opc.tcp://<host>:40451
```

Before step 3, review the generated manifest and discovered-process comment block:

- Confirm every copied process suggestion against advertised `JoiningProcessMetaData.Classification`; name hints are advisory.
- Keep `identifier_strategy: id_only` unless controller evidence requires OriginId or SelectionName.
- Keep real endpoints, Tool PIUs, serial numbers, and process identifiers only in this ignored local manifest.
- Set `max_start_invocations` to a conservative safety cap. Pacing and queue inspection reduce extra-start races but cannot make the server interaction atomic.

If recreating controller programs or sequences makes an existing exact selector
stale, use the prepared environment and refresh the ignored local manifest:

```powershell
python run_all_tests.py refresh-profile --profile .\target_server_cu_profiles\controller.sut.yaml
```

This reads the saved endpoint's live catalog and asks for explicit process
choices, an identifier-only diff review and typed save confirmation. It does
not run workloads or change claims, identifier strategies, security or risk
approvals. Multiple advertised aliases are never guessed when a selection
name is used or stored. Cancel leaves the manifest unchanged. Follow the
[refresh guide](../docs/TARGET_SERVER_CU_GUIDE.md#refresh-stale-ids-without-rebuilding-the-manifest),
then rerun preflight before separately approving workloads.

---

## Learn more

- **[SUT Manifest Field Reference](../docs/SUT_MANIFEST_REFERENCE.md)** — every field, type, default, and allowed value
- **[Target Server CU Guide](../docs/TARGET_SERVER_CU_GUIDE.md)** — architecture, controller setup, execution recipes, result layering & safety semantics
- **[Reporting Glossary & KPIs](../docs/REPORT_GLOSSARY.md)** — metric definitions, outcome statuses, and report contracts
- **[Test Report Formats](../docs/test-results.md)** — JSON schemas, JUnit XML, and Excel generation
