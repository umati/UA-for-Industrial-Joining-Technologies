---
name: associated-entities-interpreter
description: Interpret associated entities in result payloads using project source-of-truth model files and entity type mappings.
metadata:
  short-description: Interpret associated entities
---
# Associated Entities Interpreter

Interpret associated entities in result payloads using project source-of-truth model files.

## Key Principles

1. Treat `EntityDataType.EntityTypes` as the canonical source for `EntityType` labels.
2. Keep both raw and mapped type values in output.
3. Do not infer missing values or mutate payloads when the request is interpretation only.

## Source-of-Truth Files

- `src/javascripts/ijt-support/models/results/result-meta-data.mjs`
- `src/javascripts/ijt-support/models/entities/entity-data-type.mjs`
- `src/javascripts/ijt-support/models/results/result-data-type.mjs`

## Entity Type Clarifications

Use these clarifications for common IJT semantics when explaining mapped types:

- `2` (`asset`): reference to a physical asset.
- `3` (`controller`): reference to a controller asset.
- `4` (`tool`): reference to a tool asset.
- `5` (`servo`): reference to a servo asset.
- `6` (`memory_device`): reference to a memory device asset.
- `13` (`sub_component`): subcomponent of another asset.
- `14` (`software`): specific software asset.
- `15` (`result`): result produced by an executed action.
- `16` (`event`): event reference.
- `18` (`system`): system-level reference.
- `19` (`log`): specific log file reference.
- `20` (`vehicle`): vehicle reference (often VIN-level identity).
- `22` (`part`): specific part in a product.
- `23` (`joint`): product joint that describes the joining location and associated joining program.
- `26` (`joining_process`): program executed for a joining action (for example tightening program/PSET, batch, or job).
- `28` (`job`): job joining process, using single or batch joining processes.
- `29` (`batch`): batch joining process for repeated executions.
- `38` (`location`): specific location reference.
- `39` (`user`): operator/user identity (human or automated actor).
- `40` (`parent`): parent relationship (for example, a tightening result referencing its batch result).
- `41` (`virtual_station`): controller abstraction encapsulating configuration/execution for a handheld tool or fixtured multi-spindle system.

## Workflow

1. Read `ResultMetaData.mjs` and confirm `AssociatedEntities` is cast as `EntityDataType`.
2. Read `EntityDataType.mjs` and resolve:
   - entity fields
   - `EntityTypes` numeric-to-name mapping
3. For each item in `ResultMetaData.AssociatedEntities`, extract:
   - `Name`
   - `EntityId`
   - `EntityOriginId`
   - `IsExternal`
   - `EntityType`
4. Convert `EntityType` using `EntityTypes[EntityType]`.
5. If mapping key is missing, label as `unknown(<value>)` and keep the raw numeric value.
6. Present:
   - a compact per-entity interpretation
   - a short plain-language summary of what the result is linked to

## Output Format

Use this structure when summarizing associated entities:

```text
AssociatedEntities interpretation
- Name: <Name>
- EntityId: <EntityId>
- OriginId: <EntityOriginId>
- IsExternal: <true|false>
- EntityType: <numeric> -> <mapped name>
```

If no associated entities exist, state that explicitly.

## Safety Rules

1. Do not invent entity type labels; use only `EntityTypes` mapping from `EntityDataType.mjs`.
2. Do not mutate the result payload when the request is interpretation only.
3. Preserve both raw and mapped entity type values in explanations.
4. Prefer model getters/normalized fields if both raw and wrapped payload structures are present.

## Completion Checklist

1. Confirm `AssociatedEntities` was read from `ResultMetaData`.
2. Confirm `EntityType` mapping used `EntityTypes`.
3. Confirm unknown type ids are flagged, not silently converted.
4. Summarize entity links in plain language after the per-entity listing.

