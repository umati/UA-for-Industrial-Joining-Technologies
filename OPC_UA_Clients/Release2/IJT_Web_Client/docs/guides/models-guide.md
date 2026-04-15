# Models Guide

This guide explains how the model layer in `Javascripts/ijt-support/Models` works and how to change it safely.

## Purpose

The model layer converts OPC UA payloads (events, reads, result content) into structured JS classes.
Core goals:
- normalize mixed payload shapes (`Value`, `ExtensionObject`, flattened event fields),
- cast nested objects into typed models,
- connect results/entities/joints to managers and UI code.

## Main Files

- `ModelManager.mjs`: central factory and top-level routing.
- `IJTBaseModel.mjs`: recursive object/array casting engine.
- `DefaultNode.mjs`: model for browsed address-space nodes.
- `SupportModels.mjs`: helper models (`LocalizationModel`, `NodeId`, etc.).

Domain folders:
- `Results/`: tightening/job/batch/result models and trace models.
- `Events/`: event models (joining system events, result-ready events).
- `Entities/`: entity model + `EntityTypes`.
- `Joints/`: joint model.

## Construction Flow

1. Raw payload enters via `ModelManager`:
- `createModelFromEvent(msg)`
- `createModelFromRead(values)`
- `createModelFromNode(node)`

2. `ModelManager.factory(parameterName, content, castMapping)` decides class:
- uses explicit `castMapping` first,
- then falls back to simple type handlers (`LocalizationModel`, `NodeId`),
- else creates `IJTBaseModel`.

3. `IJTBaseModel` recursively walks properties:
- arrays -> maps each element through factory,
- objects -> factory,
- primitives -> direct assignment,
- ignores `pythonclass`.

## Result Model Routing

In `ModelManager.factory`, when `ResultMetaData.CreationTime` exists, result classification decides type:
- `4` -> `JobDataModel`
- `3` -> `BatchDataModel`
- `1` -> `TighteningDataType`
- default -> `ResultDataType`

`resultTypeNotification(result)` is emitted for these typed results.

## Important Side Effects

Some model constructors update managers:
- `Entities/EntityDataType.mjs` -> `modelManager.entityManager.addEntity(this)`
- `Joints/JointDataType.mjs` -> `modelManager.jointManager.addEntity(this)`

Do not remove these unless you also refactor all manager/UI consumers.

## Case/Key Mapping Notes

Payload keys are mixed case and sometimes transformed.
Examples:
- `JoiningResultDataType` cast map uses lower-case keys (`stepResults`, `resultMetaData`, `trace`) that map incoming structures into PascalCase properties after model construction.
- Event models in `Events/` clean flattened names like `JoiningSystemEventContent/...` and `Result/...`.

When adding new mappings, match the incoming key names exactly as seen in payloads.

## References and Linking

`Results/TighteningTraceDataType.mjs` creates bidirectional links between trace and step via:
- `StepResultId = { type: 'linkedValue', value, link }`
- `StepTraceId = { type: 'linkedValue', value, link }`

UI/logic depends on this link shape. Keep `type`, `value`, and `link` fields unchanged.

## Safe Change Checklist For Agents

Before edits:
- identify whether change impacts parsing, casting, side effects, or UI assumptions.

During edits:
- keep constructor signatures stable,
- keep cast mappings explicit,
- avoid removing manager side effects,
- preserve `ClientData.rebuildState` usage in result models.

After edits:
- run `npm run lint`,
- smoke test app startup (`npm run start` + backend),
- verify one event/result path still renders in UI.

## Common Tasks

Add a new nested model type:
1. create class file under the correct domain folder,
2. add cast mapping in parent model constructor,
3. ensure `ModelManager.factory` can resolve class name (string in mapping),
4. verify payload key casing.

Add a new event field mapping:
1. update cleaner function in `Events/*`,
2. add cast mapping where needed,
3. verify both event text and result-ready flows still parse.

## Anti-Patterns

- Using ad-hoc parsing outside `ModelManager`/`IJTBaseModel`.
- Mutating payload shape in unrelated UI code.
- Replacing linked-value objects with raw IDs.
- Removing fallback behavior for unknown classifications/types.
