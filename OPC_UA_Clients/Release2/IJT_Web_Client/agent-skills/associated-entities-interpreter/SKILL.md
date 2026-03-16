---
name: associated-entities-interpreter
description: Interpret `ResultMetaData.AssociatedEntities` in IJT results using `EntityDataType` and the canonical `EntityTypes` mapping. Use when requests ask to explain associated entities, classify entity types, or validate entity links in result payloads.
---

# Associated Entities Interpreter

Interpret associated entities in results using project source-of-truth model files.
Use the following clarifications of the most important entity types to understand the purpose of an entity type
  2: 'asset', This is a reference to a physical asset
  3: 'controller', This is a reference to a controller asset
  4: 'tool', this is a reference to a tool asset
  5: 'servo', this is a reference to a servo asset
  6: 'memory_device', this is a reference to a memory device asset
  7: 'sensor',
  8: 'cable',
  9: 'battery',
  10: 'power_supply',
  11: 'feeder',
  12: 'accessory',
  13: 'sub_component', this is a reference to a subcomponent asset of an asset
  14: 'software', this is a reference to a specific software asset
  15: 'result', this is a reference to a result from a device that executed an action
  16: 'event', this is an event reference
  17: 'error',
  18: 'system', this is a reference to the system 
  19: 'log', this is a reference to a specific log file
  20: 'vehicle', this is a reference to a vehicle, often called the VIN number of a car
  21: 'product',
  22: 'part', this is a reference to a specific part in a product
  23: 'joint', this references a joint on a product that describes where several parts are joined together and the program that is supposed to be run in order to execute the joining. 
  24: 'model',
  25: 'order',
  26: 'joining_process', this is a reference to a program that was executed to create a joining, this can for example be referencing the tightening program (often called PSET), or a batch program or a job program
  27: 'program',
  28: 'job', this is a reference to a job joining process using batches or single joining processes 
  29: 'batch', this is a reference to a batch joining process used to tell the controller to make several tightening using he same program
  30: 'recipe',
  31: 'task',
  32: 'process',
  33: 'configuration',
  34: 'socket',
  35: 'channel',
  36: 'station',
  37: 'production_line',
  38: 'location', this is a reference to a specific location
  39: 'user', this is a reference to the user of the tool or device, often a human, but theoretically a robot
  40: 'parent', this is a reference to a parent entity. A single tightening result might for example be referencing the batch result as the parent
  41: 'virtual_station', this reference an abstraction in a physical controller that encaptulates the configuration and execution of a single handheld tool or a fixtured system using several spindles

## Source-of-Truth Files

- `Javascripts/ijt-support/Models/Results/ResultMetaData.mjs`
- `Javascripts/ijt-support/Models/Entities/EntityDataType.mjs`
- `Javascripts/ijt-support/Models/Results/ResultDataType.mjs`

## Workflow

1. Read `ResultMetaData.mjs` to confirm `AssociatedEntities` is cast as `EntityDataType`.
2. Read `EntityDataType.mjs` to resolve entity fields and `EntityTypes` numeric-to-name mapping.
3. For each entry in `ResultMetaData.AssociatedEntities`, extract:
   - `Name`
   - `EntityId`
   - `EntityOriginId`
   - `IsExternal`
   - `EntityType`
4. Convert `EntityType` using `EntityTypes[EntityType]`.
5. If mapping key is missing, label as `unknown(<value>)` and keep the raw numeric value.
6. Present a compact interpretation table and a short summary of what entities the result is linked to.

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
