# Result Persistence Design and Status

## Goal

Document the implemented Web Client result persistence path:
- serialize results currently in memory,
- store them as JSON files,
- reload them later into the app through the same `ResultManager.addResult(...)` flow used by live-received results,
- optionally preserve the latest browser session through capped `localStorage` auto-save/auto-restore.

Primary scope is the JS frontend result pipeline (`ResultManager` + result views).

## Non-goals (v1)

- No backend database integration.
- No binary format.
- No schema migration for multiple historical versions beyond a simple `version` field and one compatible reader.
- No merge conflict UI for duplicate IDs (deterministic replace/skip policy only).

## Current State (Relevant)

- Results are held in-memory by [result-manager.mjs](../../src/javascripts/ijt-support/results/result-manager.mjs).
- Result models are class instances (`ResultDataType`, `TighteningDataType`, etc.) with runtime helpers and `ClientData.rebuildState`.
- UI tabs subscribe through `resultManager.subscribe(...)`.
- Existing serialization reference files in the same module:
  - [result-serialization.mjs](../../src/javascripts/ijt-support/results/result-serialization.mjs)
  - [result-storage-constants.mjs](../../src/javascripts/ijt-support/results/result-storage-constants.mjs)

## Key Design Decisions

1. **Canonical persisted form is plain JSON payloads**, not class instances.
   - Persist source-like result payloads (with metadata/content) and rebuild model instances on import via `ModelManager`.
   - Avoid serializing methods/prototypes or ad-hoc runtime references.

2. **Use a file envelope with metadata + result array**.
   - One file can hold N results.
   - Include schema `version`, export timestamp, and optional app/build metadata.

3. **Import path goes through `ResultManager.addResult(...)`**.
   - Keeps existing resolve/partial/subscribe flows intact.
   - Minimizes special-case rendering logic.

4. **File I/O in browser uses Download/Upload first**.
   - Export: Blob + download (`.json`).
   - Import: file picker (`<input type="file">`).
   - Optional future enhancement: File System Access API when available.

## File Format (v1)

```json
{
  "type": "ijt-result-export",
  "version": 1,
  "exportedAt": "2026-04-24T17:00:00.000Z",
  "source": {
    "app": "ijt-web-client",
    "format": "result-bundle"
  },
  "results": [
    {
      "ResultMetaData": {},
      "ResultContent": []
    }
  ]
}
```

Notes:
- `results[]` items should be canonical result payload objects compatible with current model constructors.
- Do not persist volatile runtime fields (`ClientData`, `uniqueCounter`, runtime links, DOM-derived fields).

## Current Implementation

- Serialization lives in [result-serialization.mjs](../../src/javascripts/ijt-support/results/result-serialization.mjs).
- Storage constants live in [result-storage-constants.mjs](../../src/javascripts/ijt-support/results/result-storage-constants.mjs).
- `ResultManager` exposes `exportBundle(...)`, `importBundleFromText(...)`, `collectResultClosure(...)`, capped storage retention, and runtime model reconstruction.
- The consolidated result view exposes `Export`, `Import`, import mode, and strict-mode controls in [result-graphics.mjs](../../src/javascripts/views/complex-result/result-graphics.mjs).
- The result view auto-saves a compact bundle to `localStorage` when enabled and restores it on startup when no live results are already loaded.
- Existing unit coverage is in `tests/js/unit/result-serialization.test.mjs` and `tests/js/unit/result-manager-extended.test.mjs`.

## Current Behavior

- Export roots are selected result boxes when any checkboxes are set.
- If nothing is selected, export falls back to the latest visible box, then the latest full global result, then the latest stored result.
- Export includes hierarchical closure for nested job/batch/sync result structures and records warnings for missing referenced descendants.
- Import supports `replace` and `skip-duplicates` modes.
- Strict import fails the full import on the first invalid result; non-strict import imports valid results and reports skipped entries.
- Runtime-only fields and shortcut links are removed from stored payloads and rebuilt during import/model reconstruction.
- Session persistence uses the same bundle parser/import path as file import.

## Data Integrity + Safety

- Validate incoming JSON before import:
  - top-level object shape,
  - `type === "ijt-result-export"`,
  - `version === 1`,
  - `results` is array of objects.
- Reject unknown or malformed bundles with clear user-facing error.
- Guard against prototype pollution keys (`__proto__`, `constructor`, `prototype`) during import normalization.
- Keep imports side-effect free until validation passes.

## Cybersecurity Requirements (Mandatory)

The implementation must satisfy all items below before release:

- Strict schema gate before processing any imported content.
- Hard limits for:
  - maximum file size,
  - maximum results count per import,
  - optional maximum nesting depth (to reduce parser abuse risk).
- Prototype pollution protection by rejecting/sanitizing dangerous keys:
  - `__proto__`,
  - `constructor`,
  - `prototype`.
- No dynamic code execution paths:
  - no `eval`,
  - no `Function(...)`,
  - no content-driven module loading.
- Imported values must never be rendered as HTML:
  - UI output uses text-safe rendering (`textContent`) only.
- Deterministic duplicate-ID handling:
  - explicit `skip` or `replace`, no implicit merge heuristics.
- Error messages must be user-safe:
  - no stack traces or internal path disclosure in UI feedback.
- Same validation path for local restore as for file import.

## Compatibility Strategy

- Keep `version` in file envelope from day one.
- Current parser accepts v1 envelopes plus legacy array/object bundles normalized to the v1 envelope shape.
- Unknown non-legacy `type` or `version` values fail with an explicit unsupported/invalid bundle error.
- Future versions should add per-version readers while preserving `results[]` payload compatibility where feasible.

## Backward Compatibility Policy

- Goal: load older result files when feasible, even after model evolution.
- Approach:
  - Keep the v1 reader stable.
  - Add per-version readers/mappers (`parseV2`, `parseV3`, ...) only when a new envelope version is introduced.
  - Prefer tolerant parsing for additive model changes (missing optional fields get defaults).
  - Preserve stable core identifiers (`ResultMetaData.ResultId`, classification, timestamps) across versions.
- If a result item cannot be safely mapped to current model:
  - Skip that result item only (do not fail whole import by default).
  - Record structured skip reason (for example: unsupported version, missing required fields, invalid shape).
- Offer import modes:
  - `strict`: fail the whole import on first invalid result.
  - `best-effort` (default): import valid results, skip invalid ones with reporting.

## Skip Behavior + User Notice (Mandatory)

- After each import, show an explicit summary to the user:
  - total results in file,
  - imported count,
  - skipped count.
- If any results are skipped, surface a visible warning status in UI.
- Provide a concise skip-reason summary (grouped counts by reason), for example:
  - `unsupported_result_version: 3`
  - `missing_required_fields: 5`
  - `invalid_result_shape: 2`
- Do not expose stack traces in UI.
- Log detailed diagnostics only to developer console/log channel.

## Coverage Expectations

- Unit coverage should keep protecting:
  - single-result serialization,
  - bundle metadata,
  - malformed file rejection,
  - legacy array/object bundle normalization,
  - best-effort import skip accounting,
  - strict import failure behavior,
  - prototype-pollution key filtering,
  - unknown `type`/unsupported `version` rejection,
  - over-limit file payload/count rejection,
  - duplicate-ID import behavior (`skip-duplicates`/`replace`),
  - circular reference and depth guardrails,
  - hierarchical closure and missing descendant warnings.
- Manual or E2E coverage should verify export/import from the consolidated result UI after a page reload.

## Resolved Decisions

1. Import duplicate policy default is `replace`; UI now also exposes `skip-duplicates` and `strict` options.
2. Export scope default is:
   - selected root rows when checkboxes are set,
   - otherwise fallback to latest full result (then latest available if full is unavailable).
3. Runtime shortcuts and unresolved/rebuild helper state are not persisted directly:
   - link shortcuts are removed from stored payloads and re-established during model reconstruction.
4. Guardrails are enforced in parser/serializer:
   - max file size and max result count are validated,
   - depth limit and circular reference checks prevent runaway recursion.

## Remaining Follow-ups

1. Add Playwright roundtrip coverage if UI-level export/import regression protection is needed.
2. Add a `clearAll()` manager API only if a future UX needs explicit “replace all existing results” behavior.
3. Add File System Access API support only as an optional convenience; Blob download/upload remains the supported baseline.

## Implemented Acceptance Criteria

- User can export current results to `.json`.
- User can import same file after reload and see equivalent results in UI.
- Trace and consolidated result screens work with imported data.
- Duplicate handling is deterministic and documented.
- Validation rejects malformed/unsupported bundles gracefully.
- Cybersecurity requirements in this design are implemented in the parser/serializer path.
- Backward-compatible import path exists for v1 plus legacy array/object bundles.
- Unsupported/unacceptable result entries are skipped in best-effort mode with explicit user notice.
- Unit tests cover serialization and import core paths.

## Hierarchical Export Behavior (Job/Batch/Fixtured-Sync Closure)

- Export supports hierarchical closure.
- When user exports a parent result (for example Job, Batch, or fixtured/sync result container), the exported bundle must include all internal sub-results recursively.
- Export resolves reference children by `ResultMetaData.ResultId` from the current `ResultManager` cache.
- Export must deduplicate by ResultId so shared descendants appear once.
- If some referenced descendants are not present in cache, export continues but records warnings.

### Implementation Notes

- Closure collection is implemented in `ResultManager.collectResultClosure(rootResults)`.
- Traversal contract:
  - walk `ResultContent` recursively,
  - detect result references,
  - include resolved descendants,
  - protect against cycles and repeated nodes.
- Export order must be deterministic and covered by tests.

### User Notice Requirements

- Export summary should include:
  - selected roots,
  - total exported results,
  - missing descendant references (if any).
- Missing descendants should not hard-fail export in default mode.
- Import summary should still show skipped counts/reasons when content is incomplete.

### Additional Coverage Expectations

- Exporting a Job includes all nested Batch/Tightening descendants.
- Exporting a Batch includes all nested Tightening descendants.
- Exporting a fixtured/sync parent result includes all nested descendants relevant to that result tree.
- Shared descendants are exported once (dedup by ResultId).
- Missing referenced descendants are reported in warnings with stable reason key:
  - `missing_referenced_subresult`.

### Closure Acceptance

- Exporting a Job/Batch/fixtured-sync parent produces a self-contained bundle including recursive sub-results (as available in cache).
- If some descendants are unavailable, export completes with explicit user warning.

## UI Selection Behavior for Export

- In the consolidated result view, each top-level result row/card has a selection checkbox.
- Export target selection rules:
  - If one or more rows are checked, export only those selected roots (with hierarchical closure rules applied).
  - If no rows are checked, default export target is the latest visible result box, then latest full global result, then latest stored result.
- Selection state is UI-only and must not mutate the underlying result model objects.
- Import/export status text should include whether export was selection-based or fallback-based.

### UI Selection Tests

- Checked rows only: export includes selected roots and excludes unchecked roots.
- Empty selection fallback: export includes latest full result box.
- Mixed hierarchy selection: selected parent rows include recursive descendants via closure export.
- Accessibility: checkbox is keyboard reachable and has clear label text.

### UI Selection Acceptance

- User can explicitly choose which top-level rows are included in save via upper-right checkboxes.
- No selection results in stable fallback behavior: save latest full result box.
