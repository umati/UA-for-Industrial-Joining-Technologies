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

---

## Learn more

- **[SUT Manifest Field Reference](../docs/SUT_MANIFEST_REFERENCE.md)** — every field, type, default, and allowed value
- **[Target Server CU Guide](../docs/TARGET_SERVER_CU_GUIDE.md)** — architecture, controller setup, execution recipes, result layering & safety semantics
- **[Reporting Glossary & KPIs](../docs/REPORT_GLOSSARY.md)** — metric definitions, outcome statuses, and report contracts
- **[Test Report Formats](../docs/test-results.md)** — JSON schemas, JUnit XML, and Excel generation
