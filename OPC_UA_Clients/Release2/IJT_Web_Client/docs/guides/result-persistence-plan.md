# Result Persistence Plan (Serialize -> File -> Reload)

## Goal

Enable users to:
- serialize results currently in memory,
- store them as files,
- reload them later into the app with the same behavior as live-received results.

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

## Proposed File Format (v1)

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

## Implementation Plan

## Phase 1: Serialization Core

- Add `src/javascripts/ijt-support/results/result-serialization.mjs`:
  - `serializeResultForStorage(resultModel)`
  - `serializeResultBundle(results, options?)`
  - `parseResultBundle(rawText)`
  - `validateResultBundle(bundle)` (shape + required keys + safe limits)
- Include defensive limits:
  - max file size (configurable),
  - max result count (configurable),
  - strict `type/version` check.

Deliverable:
- Pure utility module with unit tests (no UI wiring yet).

## Phase 2: ResultManager Integration

- Extend `ResultManager` with explicit persistence APIs:
  - `exportBundle({ typeFilter, includeUnresolved })`
  - `importBundle(bundle, { mode })` where `mode` is `skip-duplicates` or `replace`.
  - `clearAll()` (optional, for “replace all” workflows).
- Duplicate policy (v1 recommendation):
  - default: `replace` by `ResultMetaData.ResultId` via existing `handlePartial`/replace logic.
- Ensure `lastResult`, `results`, `unresolved`, and subscriber notifications remain consistent.
- Runtime-only manager state is not persisted directly:
  - `lastResult`, `unresolved`, `ClientData.rebuildState`, and UI-only fields are rebuilt/recomputed during import via normal `addResult(...)` flow.

Deliverable:
- Persistence-aware manager methods + tests for add/import/duplicate semantics.

## Phase 3: UI Controls

- In consolidated result view ([result-graphics.mjs](../../src/javascripts/views/complex-result/result-graphics.mjs)):
  - Add `Export Results` button.
  - Add `Import Results` button.
  - Add status messages for success/failure and counts imported/skipped/replaced.
- UX defaults:
  - Export current filter type by default (or all results if no filter selected).
  - Import appends/merges (safe default), with optional “replace existing IDs” toggle.

Deliverable:
- End-to-end manual flow: export file -> reload page -> import file -> results visible in tabs.

## Phase 4: Persistence to Local Browser Storage (Optional v1.5)

- Add session persistence:
  - On each `addResult`, debounce-save a compact bundle to `localStorage`.
  - On startup, prompt user to restore last session results.
- Use capped retention to avoid oversized storage (e.g., last N results).

Deliverable:
- Crash/reload resilience without file roundtrip.

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
- Implement a small reader switch:
  - `if version===1 -> parseV1`
  - else -> explicit unsupported-version error.
- Future versions can add optional fields while preserving `results[]` payload compatibility.

## Backward Compatibility Policy

- Goal: load old result files when feasible, even after model evolution.
- Approach:
  - Keep per-version readers/mappers (`parseV1`, `parseV2`, ...).
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

## Testing Plan

- Unit tests (new):
  - serialize single result,
  - serialize bundle metadata,
  - parse/validate malformed files,
  - parse older supported versions via versioned readers,
  - best-effort import skips invalid items and imports valid items,
  - strict import fails on first invalid item,
  - skip-reason aggregation is deterministic,
  - reject prototype-pollution payloads,
  - reject unknown `type`/unsupported `version`,
  - reject over-limit file payloads/counts,
  - duplicate ID import behavior (`skip`/`replace`),
  - large bundle guardrails.
- Integration tests:
  - import bundle triggers existing subscribers,
  - imported tightening results still render in trace and consolidated views.
- E2E smoke (Playwright):
  - export file exists,
  - import file restores result list and latest selection behavior.

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

## Suggested Task Breakdown (Ticket-sized)

1. Create serialization module + unit tests.
2. Add `ResultManager.exportBundle/importBundle`.
3. Add UI buttons in consolidated result view.
4. Add import/export status and error handling.
5. Add optional localStorage auto-restore.
6. Add E2E flow test for roundtrip.

## Acceptance Criteria (Definition of Done)

- User can export current results to `.json`.
- User can import same file after reload and see equivalent results in UI.
- Trace and consolidated result screens work with imported data.
- Duplicate handling is deterministic and documented.
- Validation rejects malformed/unsupported bundles gracefully.
- Cybersecurity requirements in this plan are implemented and tested.
- Backward-compatible import path exists for supported older versions.
- Unsupported/unacceptable result entries are skipped in best-effort mode with explicit user notice.
- Unit tests cover serialization and import core paths.

## Hierarchical Export Requirement (Job/Batch/Fixtured-Sync Closure)

- Export must support hierarchical closure.
- When user exports a parent result (for example Job, Batch, or fixtured/sync result container), the exported bundle must include all internal sub-results recursively.
- Export should resolve reference children by `ResultMetaData.ResultId` from the current `ResultManager` cache.
- Export must deduplicate by ResultId so shared descendants appear once.
- If some referenced descendants are not present in cache, export continues but records warnings.

### Implementation Notes

- Add closure collector in ResultManager persistence path, for example:
  - `collectResultClosure(rootResults, options?)`
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

### Additional Tests

- Exporting a Job includes all nested Batch/Tightening descendants.
- Exporting a Batch includes all nested Tightening descendants.
- Exporting a fixtured/sync parent result includes all nested descendants relevant to that result tree.
- Shared descendants are exported once (dedup by ResultId).
- Missing referenced descendants are reported in warnings with stable reason key:
  - `missing_referenced_subresult`.

### Acceptance Additions

- Exporting a Job/Batch/fixtured-sync parent produces a self-contained bundle including recursive sub-results (as available in cache).
- If some descendants are unavailable, export completes with explicit user warning.

## UI Selection Behavior for Export

- In the consolidated result view, each top-level result row/card must have a selection checkbox in the upper-right corner.
- Export target selection rules:
  - If one or more rows are checked, export only those selected roots (with hierarchical closure rules applied).
  - If no rows are checked, default export target is the latest full result box.
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
