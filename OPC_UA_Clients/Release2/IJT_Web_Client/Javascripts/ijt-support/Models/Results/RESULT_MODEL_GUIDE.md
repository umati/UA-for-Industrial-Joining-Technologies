# Result Model Guide

This file explains how result models in this folder are built and used.

## Goal

The result model turns OPC UA result payloads into a predictable object graph used by:
- result rendering UI,
- trace visualization,
- envelope/limit checks,
- result hierarchy (job -> batch -> tightening).

## Main Classes

- `ResultDataType.mjs`:
  base model for all results.
- `TighteningDataType.mjs`:
  specialization for single tightening results (classification `1`).
- `BatchDataType.mjs`:
  specialization for batch results (classification `3`).
- `JobDataModel.mjs`:
  specialization for job results (classification `4`).
- `JoiningResultDataType.mjs`:
  model for items inside `ResultContent`.
- `StepResultDataType.mjs`:
  model for step-level result values.
- `ResultMetaData.mjs`:
  metadata model (ID, classification, timing, etc.).
- `ResultCounters.mjs`:
  counters in metadata.
- `ResultValueDataType.mjs`:
  individual result value entries.
- `TighteningTraceDataType.mjs` (+ step/trace content types):
  trace model used for graphing and envelope logic.

## Type Routing (important)

`ModelManager.factory()` chooses concrete result class by `ResultMetaData.Classification`:
- `1` -> `TighteningDataType`
- `3` -> `BatchDataModel`
- `4` -> `JobDataModel`
- other -> `ResultDataType`

So downstream code can branch by class behavior instead of parsing raw payload each time.

## Common Result Shape

After parsing, a result object usually looks like:

```text
ResultDataType / TighteningDataType / BatchDataModel / JobDataModel
  ResultMetaData (ResultMetaData)
    ResultId
    Name
    Classification
    ResultEvaluation
    CreationTime
    ProcessingTimes
    ResultCounters (ResultCounters[])
    AssociatedEntities (EntityDataType[])
  ResultContent (JoiningResultDataType[])
    StepResults (StepResultDataType[])
      StepResultValues (ResultValueDataType[])
    Trace (TighteningTraceDataType)
      StepTraces (StepTraceDataType[])
        StepTraceContent (TraceContentDataType[])
```

## Key Helper Properties (ResultDataType)

The base class exposes convenience getters used widely by UI:
- `id` -> `ResultMetaData.ResultId`
- `name` -> `ResultMetaData.Name`
- `classification` -> `ResultMetaData.Classification`
- `isPartial` -> `ResultMetaData.IsPartial === 'True'`
- `evaluation` -> true when calling evaluation() on the result
- `time` -> end time from processing times (or fallback text)
- `isReference` -> true when metadata has no `CreationTime`

It also initializes:
- `ClientData.rebuildState` (claimed/resolved/partial flags),
which other modules rely on for rebuild/merge behavior.

## Tightening-Specific Behavior

`TighteningDataType` adds trace/result helpers:
- `getStep(stepId)` to fetch a matching step from `ResultContent`.
- `simplifyAllTracePoints()` to flatten all step traces into arrays per dimension (plus `"TIME TRACE"`).
- `simplifiedTraceToStepAndIndex(idx)` to map flattened index back to source step/index.

If trace exists, it links step trace IDs and step result IDs using linked-value objects.

## Linked-Value Contract

`TighteningTraceDataType.createConnections()` rewrites references like:

```js
{
  type: 'linkedValue',
  value: '<original id>',
  link: <object reference>
}
```

Keep this shape unchanged. UI code expects `type`, `value`, and `link`.

## How UI Uses the Model

Typical usage pattern:
1. Receive parsed result from manager.
2. Read metadata via getters (`id`, `name`, `classification`, `evaluation`).
3. For tightening results:
   - use `ResultContent[0].Trace` for plotting,
   - use `StepResults` and tagged values for details,
   - use flattening helpers for envelope checks.
4. For job/batch:
   - treat as hierarchical containers in consolidated result views.

## Practical Example (safe checks)

When handling a result:

```js
if (result.classification === '1' && result.ResultContent?.[0]?.Trace) {
  const points = result.simplifyAllTracePoints()
  // use points['angle'], points['torque'], points['TIME TRACE']
}
```

## Safe Change Rules

- Do not remove or rename convenience getters in `ResultDataType`.
- Do not remove `ClientData.rebuildState` initialization.
- Preserve cast mappings in constructors.
- Preserve linked-value object format in trace-step linking.
- Keep `parameters.Value` unwrapping logic where present.

## When Adding New Result Fields

1. Add cast mapping in relevant class constructor.
2. Keep incoming key casing aligned with payload.
3. Add helper getter only if consumed in multiple places.
4. Verify:
   - lint passes,
   - tightening trace still renders,
   - job/batch hierarchy still displays.
